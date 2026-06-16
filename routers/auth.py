from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from starlette import status
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from sqlalchemy import select

from database.db import SessionLocal
from database.models import User, OAuthState

LOGGER = logging.getLogger(__name__)
auth_router = APIRouter(tags=["auth"])

# Jinja2 templates location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Initialize Authlib OAuth client
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def is_oauth_configured() -> bool:
    """Check if Google Client ID and Secret environment variables are present."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    return bool(client_id and client_secret)


@auth_router.get("/")
@auth_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Renders the login screen containing ONLY the Continue with Google button."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    configured = is_oauth_configured()
    error = request.query_params.get("error")

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "configured": configured,
            "error": error
        }
    )


@auth_router.get("/auth/google")
async def google_login(request: Request):
    """Initiates Google OAuth 2.0 flow redirection.

    Instead of relying on session cookies to persist the OAuth state
    through Google's redirect (which fails when cookies are lost due to
    cross-origin navigation or proxy interference), we:
    1. Let Authlib generate the state and write it to request.session
    2. Extract the state from the session and save it to the database
    3. The callback route reads state from the DB and injects it back
       into request.session before Authlib validates it
    """
    if not is_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured. Please define GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the environment."
        )

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", str(request.url_for("google_callback")))

    # Let Authlib generate the redirect (this writes state into request.session)
    response = await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")

    # Extract the state Authlib just wrote into the session and persist it to DB
    session_data = dict(request.session)
    print("[OAuth] Session after Authlib state generation:", session_data)

    # Find the _state_google_* key that Authlib created
    for key, val in session_data.items():
        if key.startswith("_state_google_"):
            state_token = key.replace("_state_google_", "")
            state_payload = json.dumps(val)
            print(f"[OAuth] Saving state to DB: token={state_token}")

            # Persist to database
            with SessionLocal() as db_session:
                oauth_state = OAuthState(
                    state=state_token,
                    data=state_payload,
                )
                db_session.add(oauth_state)
                db_session.commit()
            break

    return response


@auth_router.get("/auth/google/callback")
async def google_callback(request: Request):
    """Callback route receiving authorization code and fetching profile information.

    Because session cookies are lost during the Google redirect round-trip,
    we restore the OAuth state from the database into request.session before
    Authlib validates it.
    """
    if not is_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured."
        )

    # Debug: Log cookies and session state on callback
    print("[OAuth Callback] Cookies:", dict(request.cookies))
    print("[OAuth Callback] Session (before restore):", dict(request.session))

    incoming_state = request.query_params.get("state")
    print("[OAuth Callback] Incoming state from Google:", incoming_state)

    if not incoming_state:
        return RedirectResponse(url="/login?error=Missing+state+parameter+from+Google.")

    # Restore state from database into session so Authlib can validate it
    with SessionLocal() as db_session:
        oauth_state = db_session.execute(
            select(OAuthState).where(OAuthState.state == incoming_state)
        ).scalars().first()

        if not oauth_state:
            print(f"[OAuth Callback] ERROR: State '{incoming_state}' not found in database!")
            return RedirectResponse(url="/login?error=Invalid+OAuth+state.+Please+try+again.")

        # Check expiry (10 minutes)
        if datetime.utcnow() - oauth_state.created_at > timedelta(minutes=10):
            print(f"[OAuth Callback] ERROR: State '{incoming_state}' has expired!")
            db_session.delete(oauth_state)
            db_session.commit()
            return RedirectResponse(url="/login?error=OAuth+state+expired.+Please+try+again.")

        # Restore the state data into request.session for Authlib
        state_data = json.loads(oauth_state.data)
        session_key = f"_state_google_{incoming_state}"
        request.session[session_key] = state_data
        print(f"[OAuth Callback] Restored state into session: {session_key}")
        print(f"[OAuth Callback] Session (after restore):", dict(request.session))

        # Clean up used state
        db_session.delete(oauth_state)
        db_session.commit()

    # Now let Authlib validate the state and exchange the code for tokens
    try:
        token = await oauth.google.authorize_access_token(request)
        print("[TRACE 1] Raw Google OAuth response token:", token)
        LOGGER.info(f"[TRACE 1] Raw Google OAuth response token: {token}")
        
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = await oauth.google.parse_id_token(request, token)
        print("[TRACE 2] Raw userinfo response:", userinfo)
        LOGGER.info(f"[TRACE 2] Raw userinfo response: {userinfo}")
        print("[TRACE 3] Value of user_info['picture']:", userinfo.get("picture") if userinfo else None)
        LOGGER.info(f"[TRACE 3] Value of userinfo['picture']: {userinfo.get('picture') if userinfo else None}")
    except Exception as e:
        LOGGER.error(f"Google OAuth authorization callback failed: {e}")
        print(f"[OAuth Callback] Token exchange failed: {e}")
        return RedirectResponse(url="/login?error=Google+authentication+failed.+Please+try+again.")

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    full_name = userinfo.get("name") or email.split("@")[0]
    profile_picture = userinfo.get("picture")

    if not google_id or not email:
        LOGGER.error(f"Required profile parameters missing from Google response: {userinfo}")
        return RedirectResponse(url="/login?error=Profile+data+not+returned+by+Google.")

    with SessionLocal() as db_session:
        user = db_session.execute(select(User).where(User.google_id == google_id)).scalars().first()
        if not user:
            # Register new user dynamically
            user = User(
                google_id=google_id,
                email=email,
                full_name=full_name,
                profile_picture=profile_picture,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            print("[TRACE 4] Value stored in database (New User):", user.profile_picture)
            LOGGER.info(f"[TRACE 4] Value stored in database (New User): {user.profile_picture}")
        else:
            # Update user profile values
            user.full_name = full_name
            user.profile_picture = profile_picture
            user.last_login = datetime.utcnow()
            db_session.commit()
            print("[TRACE 4] Value stored in database (Existing User):", user.profile_picture)
            LOGGER.info(f"[TRACE 4] Value stored in database (Existing User): {user.profile_picture}")

        # Populate session parameters
        request.session["user_id"] = user.id
        request.session["email"] = user.email
        request.session["name"] = user.full_name
        request.session["picture"] = user.profile_picture or ""
        print("[TRACE 5] Value stored in session:", request.session["picture"])
        LOGGER.info(f"[TRACE 5] Value stored in session: {request.session['picture']}")

        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie("user_name", user.full_name)
        return response


@auth_router.get("/logout")
@auth_router.post("/logout")
def logout_action(request: Request):
    """Terminates session and deletes authentication cookies."""
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user_name")
    return response










