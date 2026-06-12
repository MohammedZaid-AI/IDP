from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse

from database.db import SessionLocal
from database.repository import (
    add_review,
    analytics_payload,
    dashboard_metrics,
    get_document,
    get_document_detail,
    list_documents,
)
from services.export_service import ExportService
from services.file_service import FileService
from services.workflow import workflow


api_router = APIRouter(prefix="/api", tags=["api"])
file_service = FileService()
export_service = ExportService()
LOGGER = logging.getLogger(__name__)
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}



@api_router.get("/metrics/dashboard")
def dashboard_metrics_api() -> JSONResponse:
    with SessionLocal() as session:
        return JSONResponse(dashboard_metrics(session))


@api_router.get("/analytics")
def analytics_api() -> JSONResponse:
    with SessionLocal() as session:
        return JSONResponse(analytics_payload(session))


@api_router.get("/documents")
def list_documents_api(request: Request) -> JSONResponse:
    params = request.query_params
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 12))
    search = params.get("search")
    document_type = params.get("document_type")
    status_value = params.get("status")
    sort = params.get("sort", "created_at")
    with SessionLocal() as session:
        documents, total = list_documents(
            session,
            search=search,
            document_type=document_type,
            status=status_value,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        payload = [
            {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "status": document.status,
                "confidence": document.confidence,
                "created_at": document.created_at.isoformat(),
            }
            for document in documents
        ]
        return JSONResponse({"items": payload, "total": total, "page": page, "page_size": page_size})


@api_router.get("/documents/{document_id}")
def document_detail_api(document_id: int) -> JSONResponse:
    with SessionLocal() as session:
        document = get_document_detail(session, document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return JSONResponse(
            {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "language": document.language,
                "confidence": document.confidence,
                "status": document.status,
                "json_output": json.loads(document.json_output or "{}"),
                "processing_time": document.processing_time,
                "page_count": document.page_count,
                "created_at": document.created_at.isoformat(),
                "reviews": [
                    {
                        "id": review.id,
                        "action": review.action,
                        "notes": review.notes,
                        "created_at": review.created_at.isoformat(),
                    }
                    for review in document.reviews
                ],
                "audit_logs": [
                    {
                        "id": log.id,
                        "event_type": log.event_type,
                        "payload": log.payload,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in document.audit_logs
                ],
            }
        )


@api_router.post("/upload")
async def upload_documents(request: Request) -> JSONResponse:
    form = await request.form()
    files = form.getlist("files")
    if not files:
        LOGGER.warning("Upload request received with no files")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    LOGGER.info("Upload request received with %s file(s)", len(files))
    results: list[dict[str, Any]] = []
    combined_results: list[dict[str, Any]] = []
    for upload in files:
        original_filename = Path(upload.filename or "uploaded_file").name
        suffix = Path(original_filename).suffix.lower()
        if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type for {original_filename}. Supported types: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP",
            )

        LOGGER.info("Processing started for %s", upload.filename)
        content = await upload.read()
        saved_path = file_service.save_upload(original_filename, content)
        result = workflow.process_file(saved_path, original_filename=original_filename)
        result_payload = result.model_dump()
        results.append(result_payload)
        combined_results.append(
            _combined_export_record(
                filename=original_filename,
                document_type=result.document_type,
                extracted_json=result.json_output,
            )
        )
        LOGGER.info("Processing completed for %s with status=%s", original_filename, result.status)
    
    excel_url = None
    export_filename = "invoice" if len(files) == 1 else "combined_export"
    if combined_results:
        print(f"Documents processed: {len(combined_results)}")
        print(combined_results)
        excel_path = export_service.export_uploaded_records(combined_results, export_filename)
        abs_excel_path = excel_path.resolve()
        LOGGER.info("Excel generated at: %s (exists=%s)", abs_excel_path, abs_excel_path.exists())
        excel_url = f"/api/download-temp?file={abs_excel_path.name}"

    LOGGER.info("Upload request completed")
    return JSONResponse({
        "message": "Documents processed",
        "results": results,
        "excel_url": excel_url,
        "excel_filename": f"{export_filename}.xlsx"
    })


def _combined_export_record(filename: str, document_type: str, extracted_json: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "filename": filename,
        "document_type": document_type,
    }
    row.update(_flatten_for_excel(extracted_json))
    return row


def _flatten_for_excel(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    flattened: dict[str, Any] = {}
    for key, item in value.items():
        column = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, dict):
            flattened.update(_flatten_for_excel(item, column))
        elif isinstance(item, list):
            flattened[column] = json.dumps(item, ensure_ascii=False)
        else:
            flattened[column] = item
    return flattened


@api_router.get("/download-temp")
def download_temp_file(request: Request) -> FileResponse:
    file = request.query_params.get("file")
    LOGGER.info("Download request received: file=%r", file)
    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file query parameter")

    # Sanitise: strip any directory traversal, keep only the bare filename
    safe_name = Path(file).name
    LOGGER.info("[download-temp] requested file=%r safe_name=%r", file, safe_name)

    # Resolve exports dir to an absolute path so FileResponse works regardless of CWD
    exports_dir = export_service.settings.exports_dir.resolve()
    target_path = exports_dir / safe_name
    file_exists = target_path.exists() and target_path.is_file()
    LOGGER.info("File existence check: path=%s exists=%s", target_path, file_exists)

    if not file_exists:
        LOGGER.error("[download-temp] file not found: %s", target_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {safe_name}"
        )

    download_name = "invoice.xlsx" if safe_name.startswith("invoice") else "combined_export.xlsx"
    LOGGER.info("[download-temp] serving %s as %r", target_path, download_name)
    return FileResponse(
        str(target_path),          # absolute path — no CWD ambiguity
        filename=download_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



@api_router.post("/documents/{document_id}/review")
async def review_document(document_id: int, request: Request) -> JSONResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    action = str(payload.get("action", "review"))
    reviewer_name = str(payload.get("reviewer_name", "reviewer"))
    notes = str(payload.get("notes", ""))
    edited_json: dict[str, Any] | None = None
    raw_json = payload.get("edited_json")
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            edited_json = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="edited_json must be valid JSON") from exc
    elif isinstance(raw_json, dict):
        edited_json = raw_json

    with SessionLocal() as session:
        document = get_document(session, document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if edited_json is not None:
            document.json_output = json.dumps(edited_json, ensure_ascii=False, indent=2)
            session.add(document)
            session.commit()
        review = add_review(
            session,
            document_id=document_id,
            reviewer_name=reviewer_name,
            action=action,
            notes=notes,
            edited_json=edited_json,
        )
        return JSONResponse({"message": "Review saved", "review_id": review.id, "status": document.status})


@api_router.get("/documents/{document_id}/download/{export_format}")
def download_document(document_id: int, export_format: str) -> FileResponse:
    with SessionLocal() as session:
        document = get_document(session, document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        record = {
            "id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "json_output": json.loads(document.json_output or "{}"),
            "confidence": document.confidence,
            "status": document.status,
            "created_at": document.created_at.isoformat(),
        }
        export_path = export_service.export_records([record], export_format=export_format, filename=f"document_{document_id}")
        return FileResponse(str(export_path), filename=export_path.name)


@api_router.get("/export")
def bulk_export(request: Request) -> FileResponse:
    params = request.query_params
    export_format = params.get("format", "xlsx")
    ids_param = params.get("ids")
    with SessionLocal() as session:
        documents, _ = list_documents(session, page=1, page_size=1000)
        selected_ids = {int(item) for item in ids_param.split(",")} if ids_param else None
        records = []
        for document in documents:
            if selected_ids and document.id not in selected_ids:
                continue
            records.append(
                {
                    "id": document.id,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "status": document.status,
                    "confidence": document.confidence,
                    "created_at": document.created_at.isoformat(),
                    "json_output": json.loads(document.json_output or "{}"),
                }
            )
        export_path = export_service.export_records(records, export_format=export_format, filename="documents_export")
        return FileResponse(str(export_path), filename=export_path.name)
