---
title: Code Review OpenEnv
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review OpenEnv

> A real-world OpenEnv environment where AI agents practice **code review** — the same task senior engineers do every day.

Live on Hugging Face Spaces: [shahidshaik9/code-review-openenv](https://huggingface.co/spaces/shahidshaik9/code-review-openenv)

---

## Why Code Review?

Code review is one of the most valuable and cognitively demanding tasks in software engineering. Every day, engineers must:
- Identify subtle bugs that tests don't catch
- Spot security vulnerabilities before they reach production
- Evaluate logic correctness under edge cases

This makes it an ideal real-world task for AI agent training — it requires deep reasoning, domain knowledge, and the ability to improve iteratively based on feedback.

---

## How It Works

The agent receives a Python code snippet with intentional bugs. It must:
1. Identify all issues with specific line references
2. Explain why each issue is a problem
3. Suggest concrete fixes

The environment scores the agent based on how many real issues it correctly identifies. Partial credit is awarded for partial coverage — the agent can improve across multiple steps.

```
Agent receives code → Reviews it → Gets scored → Tries again → Improves
```

---

## Project Structure

```
├── app.py            # FastAPI server — exposes reset/step/state/health endpoints
├── env.py            # Core environment logic (step, reset, state, reward shaping)
├── models.py         # Pydantic typed models (Observation, Action, Reward, StepResult)
├── tasks.py          # Task definitions with buggy code + deterministic graders
├── inference.py      # Baseline script — runs LLM agent against all tasks
├── openenv.yaml      # OpenEnv spec metadata
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container config for HF Spaces deployment
├── pyproject.toml    # Package config with openenv-core dependency
└── baseline_scores.json  # Recorded baseline scores
```

---

## Tasks

| Task | Difficulty | What the agent must find |
|---|---|---|
| `task_easy` | Easy | Operator bug (`=+` vs `+=`), ZeroDivisionError, type concatenation error |
| `task_medium` | Medium | Accumulation bug, counter never increments, discount logic error |
| `task_hard` | Hard | SQL injection (2 places), MD5 weak hashing, hardcoded secret key, env vars exposed, no auth check |

Each task has a **deterministic grader** — no LLM judging, no subjectivity. The grader checks whether the agent's review contains the key terms that prove it found the real issues.

---

## Observation Space

What the agent receives at each step:

```json
{
  "task_id": "task_easy",
  "difficulty": "easy",
  "code_snippet": "def calculate_average(numbers):\n    total = 0\n    ...",
  "language": "python",
  "instructions": "Review the following Python function...",
  "step_count": 0,
  "max_steps": 3,
  "history": []
}
```

## Action Space

What the agent sends:

```json
{
  "review": "Line 4 has a bug: =+ should be +=. Line 5 has no zero division guard...",
  "issues_found": ["Line 4: =+ operator bug", "Line 5: ZeroDivisionError possible"],
  "suggested_fix": "def calculate_average(numbers):\n    if not numbers: return 0\n    ..."
}
```

## Reward

```json
{
  "value": 0.87,
  "breakdown": {
    "keyword_score": 0.82,
    "fix_bonus": 0.05,
    "loop_penalty": 0.0,
    "step_bonus": 0.0
  },
  "feedback": "Correctly identified: =+, zero, division. Missed: type concatenation."
}
```

---

## Reward Function Design

The reward function is designed to provide **meaningful signal throughout the trajectory**, not just at the end:

| Component | Description | Value |
|---|---|---|
| Keyword coverage (65%) | Did the agent mention the key issues? | 0.0 – 0.65 |
| Partial keywords (35%) | Broader terms like "bug", "error", "fix" | 0.0 – 0.35 |
| Fix bonus | Agent provided a suggested fix | +0.05 |
| Length penalty | Reviews under 50 words are penalized | -0.3 to -0.7 |
| Loop penalty | Same review submitted twice | -0.15 |
| Step bonus | Agent improves review across steps | +small |

All scores are strictly between 0 and 1 (exclusive) — never exactly 0.0 or 1.0.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/reset` | Start new episode |
| POST | `/step` | Submit action, get reward |
| GET | `/state` | Current episode state |
| GET | `/tasks` | List all tasks |
| GET | `/docs` | Interactive Swagger UI |

---

## Baseline Results

Model: `meta-llama/Llama-3.3-70B-Instruct` via HF Inference API

```
[START] task=task_easy env=code-review-openenv model=meta-llama/Llama-3.3-70B-Instruct
[STEP] step=1 action=... reward=0.95 done=true error=null
[END] success=true steps=1 score=0.95 rewards=0.95

[START] task=task_medium env=code-review-openenv model=meta-llama/Llama-3.3-70B-Instruct
[STEP] step=1 action=... reward=0.84 done=false error=null
[STEP] step=2 action=... reward=0.95 done=true error=null
[END] success=true steps=2 score=0.90 rewards=0.84,0.95

[START] task=task_hard env=code-review-openenv model=meta-llama/Llama-3.3-70B-Instruct
[STEP] step=1 action=... reward=0.86 done=true error=null
[END] success=true steps=1 score=0.86 rewards=0.86

AVERAGE: 0.918
```

---

## Setup & Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "HF_TOKEN=your_token" > .env
echo "API_BASE_URL=https://router.huggingface.co/v1" >> .env
echo "MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct" >> .env
echo "ENV_BASE_URL=http://localhost:7860" >> .env

# Start the environment server
uvicorn app:app --host 0.0.0.0 --port 7860

# Run baseline inference (in another terminal)
python inference.py
```

## Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HF_TOKEN` | Yes | None | Hugging Face API token |
| `API_BASE_URL` | No | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `meta-llama/Llama-3.3-70B-Instruct` | Model identifier |
| `ENV_BASE_URL` | No | `http://localhost:7860` | Environment server URL |

---

## Author

Shaik Shahid — [shahidshaik9](https://huggingface.co/shahidshaik9) — [GitHub](https://github.com/Shahidshaik999)
