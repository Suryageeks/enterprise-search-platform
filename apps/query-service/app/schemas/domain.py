from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DomainDecision(StrEnum):
    OPERATIONAL = "operational"
    REMEDIATION = "remediation"
    OUT_OF_DOMAIN = "out_of_domain"
    UNSAFE = "unsafe"


class DomainReason(StrEnum):
    LOG_ANALYSIS = "log_analysis"
    DASHBOARD_REQUEST = "dashboard_request"
    RUNBOOK_REQUEST = "runbook_request"
    INCIDENT_REMEDIATION = "incident_remediation"
    CAPABILITY_QUESTION = "capability_question"
    UNRELATED_REQUEST = "unrelated_request"
    DATA_MUTATION = "data_mutation"
    CODE_EXECUTION = "code_execution"
    PROMPT_INJECTION = "prompt_injection"
    UNCLEAR = "unclear"


class DomainClassification(BaseModel):
    decision: DomainDecision
    reason: DomainReason
    confidence: float = Field(ge=0, le=1)
    requires_evidence: bool
    allow_code_solution: bool = False

    @model_validator(mode = "after")
    def validate_policy(self) -> "DomainClassification":
        if self.decision != DomainDecision.REMEDIATION:
            self.allow_code_solution = False
        
        if self.decision in {
            DomainDecision.OUT_OF_DOMAIN,
            DomainDecision.UNSAFE
        }:
            self.requires_evidence = False
            self.allow_code_solution = False
        
        return self

