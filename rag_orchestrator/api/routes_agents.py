from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ._state import manager, ensure_started_task
from ..agents.base import AgentSpec
from ..agents.registry import list_types

router = APIRouter()

class AgentCreateIn(BaseModel):
    agent_type: str
    name: str
    system: str | None = None
    tenant: str | None = "default"
    config: dict | None = None

class AgentRef(BaseModel):
    id: str; type: str; name: str; tenant: str

class StepIn(BaseModel):
    state: dict

class BulkCreateIn(BaseModel):
    agent_types: list[str]
    name_prefix: str
    system: str | None = None
    tenant: str | None = "default"

@router.post("/orchestrator/agents", response_model=AgentRef)
async def create_agent(inp: AgentCreateIn):
    await ensure_started_task
    h = await manager.create(inp.agent_type, AgentSpec(name=inp.name, system=inp.system, tenant=inp.tenant or "default", config=inp.config))
    return AgentRef(id=h.agent_id, type=h.agent_type, name=h.spec.name, tenant=h.spec.tenant)

@router.get("/orchestrator/agents", response_model=list[AgentRef])
async def list_agents():
    await ensure_started_task
    rows = await manager.list()
    return [AgentRef(**r) for r in rows]

@router.delete("/orchestrator/agents/{agent_id}")
async def delete_agent(agent_id: str):
    await ensure_started_task
    await manager.destroy(agent_id)
    return {"ok": True}

@router.post("/orchestrator/agents/{agent_id}/step")
async def step_agent(agent_id: str, inp: StepIn):
    await ensure_started_task
    try:
        out = await manager.step(agent_id, inp.state)
        return {"state": out}
    except KeyError:
        raise HTTPException(status_code=404, detail="agent not found")

@router.post("/orchestrator/agents/bulk")
async def bulk_create(inp: BulkCreateIn):
    await ensure_started_task
    available = set(list_types())
    missing = [t for t in inp.agent_types if t not in available]
    if missing:
        return {"ok": False, "missing": missing}
    created = []
    for i, t in enumerate(inp.agent_types, 1):
        h = await manager.create(t, AgentSpec(name=f"{inp.name_prefix}-{t}-{i}", system=inp.system, tenant=inp.tenant or "default"))
        created.append({"id": h.agent_id, "type": h.agent_type, "name": h.spec.name, "tenant": h.spec.tenant})
    return {"ok": True, "agents": created}