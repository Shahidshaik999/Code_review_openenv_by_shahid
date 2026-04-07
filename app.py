"""
FastAPI app exposing the OpenEnv Code Review Environment.
Endpoints: POST /reset, POST /step, GET /state, GET /health
Also serves the original AI Codebase Explainer routes under /api/*
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import Action, Observation, ResetRequest, StateResponse, StepResult
from env import CodeReviewEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Code Review OpenEnv",
    description="OpenEnv-compliant code review environment for AI agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared environment instance (stateful per-process)
_env = CodeReviewEnv()


# ---------------------------------------------------------------------------
# OpenEnv required endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "env": "code-review-env", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "Code Review OpenEnv",
        "description": "AI agent code review environment",
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
            "health": "GET /health",
            "docs": "/docs",
        },
        "tasks": ["task_easy", "task_medium", "task_hard", "task_very_hard", "task_expert"],
    }


@app.post("/reset", response_model=Observation)
async def reset(request: ResetRequest = None):
    """Reset the environment. Optionally specify task_id."""
    task_id = (request.task_id if request else None) or "task_easy"
    try:
        obs = _env.reset(task_id=task_id)
        logger.info(f"Reset to task: {task_id}")
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResult)
async def step(action: Action):
    """Take one step in the environment with the given action."""
    try:
        result = _env.step(action)
        logger.info(f"Step {result.observation.step_count} | reward={result.reward.value} | done={result.done}")
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateResponse)
async def state():
    """Get current environment state without side effects."""
    return _env.state()


@app.get("/tasks")
async def list_tasks():
    """List all available tasks."""
    from tasks import TASKS
    return {
        tid: {
            "id": t["id"],
            "difficulty": t["difficulty"],
            "language": t["language"],
            "instructions": t["instructions"],
        }
        for tid, t in TASKS.items()
    }
