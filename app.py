# Main entry (optional)

import uvicorn
from rag_llm_api_pipeline.api.server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
