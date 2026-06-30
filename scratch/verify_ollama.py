import httpx
import os
import dotenv

dotenv.load_dotenv()

def main():
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        # Get version
        v_res = httpx.get(f"{ollama_url}/api/version")
        version = v_res.json().get("version", "unknown")
        
        # Get models
        m_res = httpx.get(f"{ollama_url}/api/tags")
        models = [m["name"] for m in m_res.json().get("models", [])]
        
        print(f"Ollama Version: {version}")
        print(f"Loaded Models: {models}")
    except Exception as e:
        print(f"Error querying Ollama: {e}")

if __name__ == "__main__":
    main()
