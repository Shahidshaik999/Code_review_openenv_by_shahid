---
title: Code Review OpenEnv
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review OpenEnv

A real-world OpenEnv-compliant environment where AI agents practice **code review** — identifying bugs, logic errors, and security vulnerabilities in Python code snippets.

Live on Hugging Face Spaces: [shahidshaik9/code-review-openenv](https://huggingface.co/spaces/shahidshaik9/code-review-openenv)

---

## What is this?

This is an AI training environment built for the OpenEnv standard. Instead of playing games, the AI agent does something humans actually do every day — **reviewing code for bugs and security issues**.

The agent receives a buggy code snippet, analyzes it, identifies the problems, and suggests fixes. It gets scored based on how many real issues it correctly finds. The harder the task, the more issues it needs to catch to score well.

---

## Project Structure

```
├── app.py            # FastAPI server — exposes reset/step/state endpoints
├── env.py            # Core environment logic (step, reset, state, rewards)
├── models.py         # Pydantic typed models (Observation, Action, Reward)
├── tasks.py          # 3 task definitions with buggy code + deterministic graders
├── inference.py      # Baseline script — runs an LLM agent against all 3 tasks
├── openenv.yaml      # OpenEnv spec metadata
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container config for HF Spaces deployment
└── baseline_scores.json  # Recorded baseline scores
```

---

## Tasks

| Task | Difficulty | What the agent must find |
|---|---|---|
| `task_easy` | Easy | Operator bug (`=+` vs `+=`), ZeroDivisionError, type concatenation error |
| `task_medium` | Medium | Accumulation bug, counter never increments, discount logic error |
| `task_hard` | Hard | SQL injection (2 places), MD5 weak hashing, hardcoded secret key, env vars exposed, no auth check, full data exposure |
| `task_very_hard` | Very Hard | Race conditions, missing thread locks, thread-unsafe list append, missing thread joins, file resource leak |
| `task_expert` | Expert | O(n²) duplicate finder, N+1 database query, mutable default argument bug, wrong sort order |

Each task has a **deterministic grader** — it checks whether the agent's review contains the key terms that prove it found the real issues. No LLM judging, no subjectivity.

---

## OpenEnv API

The environment runs as an HTTP server on port 7860.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check — returns `{"status": "ok"}` |
| POST | `/reset` | Start a new episode, returns initial Observation |
| POST | `/step` | Submit an Action, returns Observation + Reward + done |
| GET | `/state` | Get current episode state without side effects |
| GET | `/tasks` | List all available tasks |
| GET | `/docs` | Interactive API documentation (Swagger UI) |

### Observation (what the agent receives)
```json
{
  "task_id": "task_easy",
  "difficulty": "easy",
  "code_snippet": "def calculate_average(numbers):\n    ...",
  "language": "python",
  "instructions": "Review the following Python function...",
  "step_count": 0,
  "max_steps": 3,
  "history": []
}
```

### Action (what the agent sends)
```json
{
  "review": "Line 4 has a bug: =+ should be +=. Line 5 has no zero division guard...",
  "issues_found": ["Line 4: =+ operator bug", "Line 5: ZeroDivisionError possible"],
  "suggested_fix": "def calculate_average(numbers):\n    if not numbers: return 0\n    total = 0\n    ..."
}
```

### Reward (what the agent gets back)
```json
{
  "value": 0.95,
  "breakdown": {
    "keyword_score": 0.90,
    "fix_bonus": 0.05,
    "loop_penalty": 0.0
  },
  "feedback": "Correctly identified: =+, zero, division. Missed: type concatenation."
}
```

---

## Reward Function

Rewards are **not binary** — the agent gets partial credit for partial work:

- **Keyword coverage (65%)** — did the agent mention the key issues? Each required keyword found adds to the score
- **Partial keywords (35%)** — broader terms like "bug", "error", "fix" also contribute
- **Fix bonus (+0.05)** — agent gets a small bonus for providing a suggested fix
- **Length penalty** — reviews under 50 words are penalized (encourages detailed analysis)
- **Loop penalty (-0.15)** — if the agent submits the exact same review twice, it gets penalized (prevents lazy repetition)
- **Step bonus** — if the agent improves its review across steps, it gets a small bonus

Score range: 0.0 (found nothing) to 1.0 (found everything perfectly).

---

## Baseline Results

Model used: `meta-llama/Llama-3.3-70B-Instruct` via HF Inference API

```
task_easy      (easy     ): 1.000
task_medium    (medium   ): 1.000
task_hard      (hard     ): 1.000
task_very_hard (very_hard): 0.875
task_expert    (expert   ): 0.980
AVERAGE                   : 0.971
```

---

## Setup & Run Locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file
```
HF_TOKEN=hf_your_token_here
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct
ENV_BASE_URL=http://localhost:7860
```

### 3. Start the environment server
```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

### 4. Run the baseline inference script
```bash
python inference.py
```

---

## Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `HF_TOKEN` | Yes | Hugging Face API token |
| `API_BASE_URL` | Yes | LLM API endpoint (e.g. `https://router.huggingface.co/v1`) |
| `MODEL_NAME` | Yes | Model to use (e.g. `meta-llama/Llama-3.3-70B-Instruct`) |
| `ENV_BASE_URL` | No | Environment server URL (default: `http://localhost:7860`) |

---

## Author

Shaik Shahid — [shahidshaik9](https://huggingface.co/shahidshaik9)
