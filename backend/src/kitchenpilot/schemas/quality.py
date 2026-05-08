from pydantic import BaseModel, Field


class QualityCheckResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    needs_repair: bool = False

