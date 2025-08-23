from __future__ import annotations
import os, uvicorn


def main():
    host = os.getenv("ORCH_HOST", "127.0.0.1")
    port = int(os.getenv("ORCH_PORT", "8080"))
    uvicorn.run("rag_orchestrator.api.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
