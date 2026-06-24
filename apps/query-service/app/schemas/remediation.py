from enum import StrEnum

from pydantic import BaseModel, Field


class ActionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GroundedStatement(BaseModel):
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class ProbableCause(BaseModel):
    cause: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class RecommendedAction(BaseModel):
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    risk: ActionRisk = ActionRisk.LOW


class CodeSuggestion(BaseModel):
    language: str = Field(min_length=1)
    description: str = Field(min_length=1)
    code: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class RemediationResult(BaseModel):
    summary: str = Field(min_length=1)
    observed_facts: list[GroundedStatement] = Field(min_length=1)
    probable_causes: list[ProbableCause] = Field(default_factory=list)
    diagnostic_actions: list[RecommendedAction] = Field(min_length=1)
    remediation_steps: list[RecommendedAction] = Field(default_factory=list)
    code_suggestion: CodeSuggestion | None = None
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
