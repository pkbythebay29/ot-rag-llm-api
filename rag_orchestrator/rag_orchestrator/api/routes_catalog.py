from fastapi import APIRouter
from pydantic import BaseModel

# Simple static catalog; replace with your registry if you have one
CATALOG = [
    {"slug": "retriever", "name": "Retriever Agent", "description": "Vector search."},
    {
        "slug": "compressor",
        "name": "Compressor Agent",
        "description": "Chunk/prompt compression.",
    },
    {
        "slug": "reranker",
        "name": "Reranker Agent",
        "description": "Cross-encoder re-ranking.",
    },
    {
        "slug": "drafting",
        "name": "Drafting Agent",
        "description": "Speculative decoding.",
    },
    {
        "slug": "validator",
        "name": "Validator Agent",
        "description": "Full-precision verification.",
    },
    {
        "slug": "dialogue",
        "name": "Dialogue Agent",
        "description": "Conversation memory + KV cache.",
    },
    {
        "slug": "coordinator",
        "name": "Coordinator Agent",
        "description": "Quantization + scheduling.",
    },
]

router = APIRouter()


class AgentItem(BaseModel):
    slug: str
    name: str
    description: str


class CatalogResponse(BaseModel):
    agents: list[AgentItem]


@router.get("/catalog", response_model=CatalogResponse, tags=["catalog"])
async def catalog():
    # Return under "agents" so the UI can pick the first slug
    return CatalogResponse(agents=[AgentItem(**m) for m in CATALOG])
