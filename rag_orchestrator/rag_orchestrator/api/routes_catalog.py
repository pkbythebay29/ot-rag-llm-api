from fastapi import APIRouter
from pydantic import BaseModel

CATALOG = [
  {"key":"retriever","title":"Retriever Agent","description":"Vector search.","entrypoint":"retriever"},
  {"key":"compressor","title":"Compressor Agent","description":"Chunk/prompt compression.","entrypoint":"compressor"},
  {"key":"reranker","title":"Reranker Agent","description":"Cross-encoder re-ranking.","entrypoint":"reranker"},
  {"key":"drafting","title":"Drafting Agent","description":"Speculative decoding.","entrypoint":"drafting"},
  {"key":"validator","title":"Validator Agent","description":"Full-precision verification.","entrypoint":"validator"},
  {"key":"dialogue","title":"Dialogue Agent","description":"Conversation memory + KV cache.","entrypoint":"dialogue"},
  {"key":"coordinator","title":"Coordinator Agent","description":"Quantization + scheduling.","entrypoint":"coordinator"},
]

router = APIRouter()

class CatalogItem(BaseModel):
    key: str; title: str; description: str; entrypoint: str

@router.get("/orchestrator/catalog", response_model=list[CatalogItem])
async def catalog():
    return [CatalogItem(**m) for m in CATALOG]