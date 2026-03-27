---
title: Code Review OpenEnv
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Code Review OpenEnv

A real-world OpenEnv environment where an AI agent performs code reviews — identifying bugs, logic errors, and security vulnerabilities in code snippets.

---

## Environment Description

The agent receives a code snippet and must:
1. Identify all issues (bugs, logic errors, security vulnerabilities)
2. Reference specific line numbers
3. Suggest concrete fixes

Rewards are based on how many key issues the agent correctly identifies, with partial credit for partial coverage.

---

## Tasks

| Task ID | Difficulty | Description |
|---|---|---|
| `task_easy` | Easy | Find syntax errors and simple bugs in Python |
| `task_medium` | Medium | Detect subtle logic bugs causing incorrect behavior |
| `task_hard` | Hard | Security vulnerability review (SQL injection, weak crypto, data exposure) |

---

## Action / Observation Spaces

### Observation
```json
{
  "task_id": "task_easy",
  "difficulty": "easy",
  "code_snippet": "...",
  "language": "python",
  "instructions": "Review the following...",
  "step_count": 0,
  "max_steps": 3,
  "history": []
}
```

### Action
```json
{
  "review": "Line 4 has a bug: =+ should be +=...",
  "issues_found": ["Line 4: =+ operator bug", "Line 5: ZeroDivisionError possible"],
  "suggested_fix": "def calculate_average(numbers):\n    if not numbers: return 0\n    ..."
}
```

### Reward
```json
{
  "value": 0.75,
  "breakdown": {"keyword_score": 0.7, "fix_bonus": 0.05, "loop_penalty": 0.0},
  "feedback": "Correctly identified: =+, zero division. Missed: type concatenation."
}
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/reset` | Start new episode |
| POST | `/step` | Submit action |
| GET | `/state` | Current state |
| GET | `/tasks` | List all tasks |

---

## Setup & Run

### Local
```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Docker
```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

---

## Baseline Inference

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export HF_TOKEN="your_hf_token"
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

Expected output:
```
task_easy   (easy  ): 0.650
task_medium (medium): 0.520
task_hard   (hard  ): 0.410
AVERAGE              : 0.527
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `API_BASE_URL` | LLM API endpoint |
| `MODEL_NAME` | Model identifier |
| `HF_TOKEN` | Hugging Face / API key |
| `ENV_BASE_URL` | Environment server URL (default: http://localhost:7860) |
