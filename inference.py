"""
Baseline Inference Script — Code Review OpenEnv
================================================
MANDATORY environment variables:
  API_BASE_URL  - The API endpoint for the LLM (e.g. https://router.huggingface.co/v1)
  MODEL_NAME    - The model identifier (e.g. meta-llama/Llama-3.3-70B-Instruct)
  HF_TOKEN      - Your Hugging Face API key

Runs the agent against all 3 tasks and prints reproducible baseline scores.
"""
import os
import json
import sys
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # loads .env file automatically

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

MAX_STEPS = 3
TEMPERATURE = 0.2
MAX_TOKENS = 800

TASK_IDS = ["task_easy", "task_medium", "task_hard", "task_very_hard", "task_expert"]

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
# Helpers
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
    """Call the LLM with the current observation and parse the action."""
    user_prompt = f"""Task difficulty: {observation['difficulty']}
Language: {observation['language']}
Instructions: {observation['instructions']}

Code to review:
```{observation['language']}
{observation['code_snippet']}
```

Step {observation['step_count'] + 1} of {observation['max_steps']}.
"""
    # Include history context if available
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
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
        # Fix invalid control characters (tabs, newlines inside JSON strings)
        import re as _re
        raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
        # Replace literal newlines inside JSON string values with \n escape
        raw = _re.sub(r'(?<=: ")(.*?)(?="[,\n}])', lambda m: m.group(0).replace('\n', '\\n').replace('\t', '\\t'), raw, flags=_re.DOTALL)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Last resort: extract fields manually
            review = _re.search(r'"review"\s*:\s*"(.*?)"(?=\s*,\s*"issues_found")', raw, _re.DOTALL)
            issues = _re.search(r'"issues_found"\s*:\s*\[(.*?)\]', raw, _re.DOTALL)
            fix = _re.search(r'"suggested_fix"\s*:\s*"(.*?)"(?=\s*[}\n])', raw, _re.DOTALL)
            return {
                "review": review.group(1).replace('\\"', '"') if review else raw[:500],
                "issues_found": [i.strip().strip('"') for i in issues.group(1).split('",') if i.strip()] if issues else [],
                "suggested_fix": fix.group(1) if fix else None,
            }
    except (json.JSONDecodeError, Exception) as e:
        print(f"  [WARN] LLM parse error: {e}. Using fallback action.")
        return {
            "review": "Unable to parse response. Code contains potential issues.",
            "issues_found": ["Parse error - review failed"],
            "suggested_fix": None,
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_task(client: OpenAI, task_id: str) -> float:
    print(f"\n{'='*60}")
    print(f"Task: {task_id}")
    print(f"{'='*60}")

    obs = env_reset(task_id)
    print(f"Difficulty: {obs['difficulty']} | Language: {obs['language']}")
    print(f"Instructions: {obs['instructions'][:100]}...")

    best_reward = 0.0
    done = False

    for step in range(1, MAX_STEPS + 1):
        if done:
            break

        print(f"\n  Step {step}/{MAX_STEPS}")
        action = call_llm(client, obs)

        # Ensure required fields
        action.setdefault("review", "")
        action.setdefault("issues_found", [])
        action.setdefault("suggested_fix", None)

        result = env_step(action)
        reward = result["reward"]["value"]
        done = result["done"]
        obs = result["observation"]

        print(f"  Reward: {reward:.3f} | Done: {done}")
        print(f"  Feedback: {result['reward']['feedback']}")
        if result["info"].get("required_missing"):
            print(f"  Missed: {result['info']['required_missing']}")

        if reward > best_reward:
            best_reward = reward

    state = env_state()
    print(f"\n  Final cumulative reward: {state['cumulative_reward']:.3f}")
    print(f"  Best step reward: {best_reward:.3f}")
    return best_reward


def main():
    if not API_KEY:
        print("ERROR: HF_TOKEN or API_KEY environment variable not set.")
        sys.exit(1)

    # Check env is reachable
    try:
        resp = requests.get(f"{ENV_BASE_URL}/health", timeout=10)
        resp.raise_for_status()
        print(f"Environment health: {resp.json()}")
    except Exception as e:
        print(f"ERROR: Cannot reach environment at {ENV_BASE_URL}: {e}")
        print("Make sure the environment server is running: uvicorn app:app --port 7860")
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task_id in TASK_IDS:
        try:
            score = run_task(client, task_id)
            scores[task_id] = score
        except Exception as e:
            print(f"ERROR on {task_id}: {e}")
            scores[task_id] = 0.0

    print(f"\n{'='*60}")
    print("BASELINE SCORES")
    print(f"{'='*60}")
    for task_id, score in scores.items():
        difficulty = {"task_easy": "easy", "task_medium": "medium", "task_hard": "hard", "task_very_hard": "very_hard", "task_expert": "expert"}[task_id]
        print(f"  {task_id} ({difficulty:6s}): {score:.3f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  {'AVERAGE':20s}: {avg:.3f}")
    print(f"{'='*60}")

    # Write scores to file for CI/validation
    with open("baseline_scores.json", "w") as f:
        json.dump({"scores": scores, "average": avg, "model": MODEL_NAME}, f, indent=2)
    print("\nScores saved to baseline_scores.json")


if __name__ == "__main__":
    main()
