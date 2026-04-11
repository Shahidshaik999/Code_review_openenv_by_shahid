"""
Baseline Inference Script — Code Review OpenEnv
================================================
MANDATORY environment variables:
  API_BASE_URL  - The API endpoint for the LLM
  MODEL_NAME    - The model identifier
  HF_TOKEN      - Your Hugging Face API key
  ENV_BASE_URL  - The environment server URL (default: http://localhost:7860)
"""
import os
import json
import sys
import requests
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")
API_KEY = HF_TOKEN
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
BENCHMARK = "code-review-openenv"

MAX_STEPS = 3
TEMPERATURE = 0.2
MAX_TOKENS = 800

TASK_IDS = ["task_easy", "task_medium", "task_hard"]

SYSTEM_PROMPT = """You are an expert software engineer performing a code review.
When given a code snippet, you must:
1. Identify ALL bugs, errors, and issues with specific line references
2. Explain why each issue is a problem
3. Suggest concrete fixes

Respond ONLY with a valid JSON object in this exact format:
{
  "review": "<full detailed review text>",
  "issues_found": ["<issue 1 with line number>", "<issue 2 with line number>", ...],
  "suggested_fix": "<corrected code or specific fix instructions>"
}"""


# ---------------------------------------------------------------------------
# Structured logging — MANDATORY FORMAT
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Truncate action to keep line readable
    action_short = action[:80].replace("\n", " ") if action else "null"
    print(f"[STEP] step={step} action={action_short} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    # score = average of rewards, clamped strictly between 0 and 1
    score = sum(rewards) / len(rewards) if rewards else 0.05
    score = round(min(0.95, max(0.05, score)), 2)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def env_reset(task_id: str) -> dict:
    resp = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(action: dict) -> dict:
    resp = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_state() -> dict:
    resp = requests.get(f"{ENV_BASE_URL}/state", timeout=10)
    resp.raise_for_status()
    return resp.json()


def call_llm(client: OpenAI, observation: dict) -> dict:
    user_prompt = f"""Task difficulty: {observation['difficulty']}
Language: {observation['language']}
Instructions: {observation['instructions']}

Code to review:
```{observation['language']}
{observation['code_snippet']}
```

Step {observation['step_count'] + 1} of {observation['max_steps']}.
"""
    if observation.get("history"):
        last = observation["history"][-1]
        user_prompt += f"\nYour previous review scored {last.get('reward', 0):.2f}. Improve your analysis."

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = completion.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
        import re as _re
        raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
        raw = _re.sub(r'(?<=: ")(.*?)(?="[,\n}])', lambda m: m.group(0).replace('\n', '\\n').replace('\t', '\\t'), raw, flags=_re.DOTALL)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            review = _re.search(r'"review"\s*:\s*"(.*?)"(?=\s*,\s*"issues_found")', raw, _re.DOTALL)
            issues = _re.search(r'"issues_found"\s*:\s*\[(.*?)\]', raw, _re.DOTALL)
            fix = _re.search(r'"suggested_fix"\s*:\s*"(.*?)"(?=\s*[}\n])', raw, _re.DOTALL)
            return {
                "review": review.group(1).replace('\\"', '"') if review else raw[:500],
                "issues_found": [i.strip().strip('"') for i in issues.group(1).split('",') if i.strip()] if issues else [],
                "suggested_fix": fix.group(1) if fix else None,
            }
    except Exception as e:
        return {
            "review": f"Error: {e}",
            "issues_found": [],
            "suggested_fix": None,
        }


# ---------------------------------------------------------------------------
# Run one task
# ---------------------------------------------------------------------------

def run_task(client: OpenAI, task_id: str) -> float:
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    success = False

    try:
        obs = env_reset(task_id)
        done = False

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = call_llm(client, obs)
            action.setdefault("review", "")
            action.setdefault("issues_found", [])
            action.setdefault("suggested_fix", None)

            result = env_step(action)
            reward = result["reward"]["value"]
            done = result["done"]
            obs = result["observation"]
            error = None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action["review"], reward=reward, done=done, error=error)

            if done:
                break

        success = max(rewards) >= 0.5 if rewards else False

    except Exception as e:
        log_step(step=steps_taken + 1, action="error", reward=0.05, done=True, error=str(e))
        success = False
        rewards.append(0.05)

    log_end(success=success, steps=steps_taken, rewards=rewards if rewards else [0.05])
    return max(rewards) if rewards else 0.05


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        resp = requests.get(f"{ENV_BASE_URL}/health", timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: Cannot reach environment at {ENV_BASE_URL}: {e}", flush=True)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task_id in TASK_IDS:
        try:
            score = run_task(client, task_id)
            scores[task_id] = score
        except Exception as e:
            print(f"ERROR on {task_id}: {e}", flush=True)
            scores[task_id] = 0.0

    avg = sum(scores.values()) / len(scores)
    print(f"\nBASELINE SCORES", flush=True)
    for task_id, score in scores.items():
        print(f"  {task_id}: {score:.3f}", flush=True)
    print(f"  AVERAGE: {avg:.3f}", flush=True)

    with open("baseline_scores.json", "w") as f:
        json.dump({"scores": scores, "average": avg, "model": MODEL_NAME}, f, indent=2)


if __name__ == "__main__":
    main()
