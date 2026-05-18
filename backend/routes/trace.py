from fastapi import APIRouter
from datetime import datetime
from ..db.schemas import CausalTraceRequest
from ..services.causal_tracer import trace_causal_chain
from ..services.output_writer import write_causal_trace

router = APIRouter()


@router.post("/analyze")
async def analyze_trace(req: CausalTraceRequest):
    result = await trace_causal_chain(
        outcome_description=req.outcome_description,
        outcome_date=req.outcome_first_observed,
        affected_metric=req.affected_metric,
        demo_scenario=req.demo_scenario,
    )
    write_causal_trace(result)
    return result


@router.get("/demo/{scenario}")
async def get_demo_trace(scenario: str):
    result = await trace_causal_chain(
        outcome_description=f"Demo scenario: {scenario}",
        outcome_date=datetime.utcnow(),
        affected_metric="churn_rate",
        demo_scenario=scenario,
    )
    write_causal_trace(result)
    return result
