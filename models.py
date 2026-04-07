"""
OpenEnv typed Pydantic models for the Code Review Environment.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Observation(BaseModel):
    task_id: str
    difficulty: str  # easy | medium | hard
    code_snippet: str
    language: str
    instructions: str
    step_count: int = 0
    max_steps: int = 3
    history: List[Dict[str, Any]] = Field(default_factory=list)


class Action(BaseModel):
    review: str = Field(..., description="Full review text identifying issues and suggesting fixes")
    issues_found: List[str] = Field(default_factory=list, description="List of specific issues identified")
    suggested_fix: Optional[str] = Field(None, description="Corrected code or fix instructions")


class Reward(BaseModel):
    value: float = Field(..., gt=0.0, lt=1.0)
    breakdown: Dict[str, float] = Field(default_factory=dict)
    feedback: str = ""


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class ResetRequest(BaseModel):
    task_id: Optional[str] = None  # if None, picks task_easy by default


class StateResponse(BaseModel):
    task_id: str
    difficulty: str
    step_count: int
    done: bool
    cumulative_reward: float
    current_observation: Optional[Observation] = None
