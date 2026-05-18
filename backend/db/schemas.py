from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    pricing = "pricing"
    hiring = "hiring"
    product = "product"
    strategy = "strategy"
    operational = "operational"
    unknown = "unknown"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class MetricsSnapshot(BaseModel):
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    mrr: Optional[float] = None
    arr: Optional[float] = None
    churn_rate: Optional[float] = None
    nps: Optional[int] = None
    active_customers: Optional[int] = None
    cac: Optional[float] = None
    ltv: Optional[float] = None
    support_tickets_7d: Optional[int] = None
    pipeline_value: Optional[float] = None
    burn_rate: Optional[float] = None
    runway_months: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class DecisionLogRequest(BaseModel):
    decision_text: str
    decision_type: DecisionType = DecisionType.unknown
    rationale: Optional[str] = None
    alternatives_considered: List[str] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)


class DecisionDocument(BaseModel):
    decision_id: str
    logged_at: datetime
    logged_by: str = "user"
    auto_detected: bool = False
    detection_source: Optional[str] = None
    decision_text: str
    decision_type: DecisionType
    rationale: Optional[str] = None
    alternatives_considered: List[str] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)
    metrics_snapshot: Optional[MetricsSnapshot] = None
    outcome: Optional[str] = None
    outcome_recorded_at: Optional[datetime] = None
    warning_fired: bool = False
    warning_fired_at: Optional[datetime] = None
    days_of_warning: Optional[int] = None
    causal_correlation: Optional[float] = None
    output_file: Optional[str] = None


class CausalTraceRequest(BaseModel):
    outcome_description: str
    outcome_first_observed: datetime
    affected_metric: str
    demo_scenario: Optional[str] = None


class CausalChainEvent(BaseModel):
    event_id: str
    date: datetime
    type: str  # "decision" | "signal" | "outcome"
    title: str
    description: str
    metric_value: Optional[float] = None
    metric_label: Optional[str] = None
    severity: Optional[str] = None


class CausalTraceResult(BaseModel):
    trace_id: str
    outcome_description: str
    root_decision: DecisionDocument
    causal_chain: List[CausalChainEvent]
    pearson_r: float
    p_value: float
    days_of_warning: int
    earliest_signal_date: datetime
    data_available_at_decision: Dict[str, Any]
    data_that_predicted_outcome: List[str]
    recommended_actions: List[str]
    narrative: str


class EarlyWarning(BaseModel):
    warning_id: str
    fired_at: datetime
    severity: Severity
    trigger_metric: str
    trigger_value: float
    root_decision_id: Optional[str] = None
    days_since_decision: Optional[int] = None
    causal_confidence: float
    message: str
    recommended_action: str
    acknowledged: bool = False
    demo_scenario: Optional[str] = None


class AskRequest(BaseModel):
    question: str
    demo_scenario: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    relevant_decisions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    sources: List[str] = Field(default_factory=list)
