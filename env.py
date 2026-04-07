"""
Code Review OpenEnv Environment
Implements: reset() / step() / state() per OpenEnv spec.
"""
import copy
from typing import Optional
from models import (
    Action, Observation, Reward, StepResult, StateResponse
)
from tasks import TASKS, grade_action


class CodeReviewEnv:
    """
    OpenEnv-compliant environment for AI-driven code review.

    The agent receives a code snippet and must identify bugs/issues
    and suggest fixes. Rewards are based on coverage of key issues.
    """

    def __init__(self):
        self._task_id: Optional[str] = None
        self._step_count: int = 0
        self._done: bool = False
        self._cumulative_reward: float = 0.0
        self._current_obs: Optional[Observation] = None
        self._history = []

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------

    def reset(self, task_id: Optional[str] = None) -> Observation:
        """Reset the environment to a fresh episode."""
        task_id = task_id or "task_easy"
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS.keys())}")

        task = TASKS[task_id]
        self._task_id = task_id
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._history = []

        self._current_obs = Observation(
            task_id=task_id,
            difficulty=task["difficulty"],
            code_snippet=task["code_snippet"],
            language=task["language"],
            instructions=task["instructions"],
            step_count=0,
            max_steps=task["max_steps"],
            history=[],
        )
        return self._current_obs

    def step(self, action: Action) -> StepResult:
        """
        Process one agent action and return (observation, reward, done, info).
        Penalizes repeated identical actions (loop detection).
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        if self._current_obs is None:
            raise RuntimeError("Call reset() before step().")

        self._step_count += 1

        # Loop / repetition penalty
        loop_penalty = 0.0
        if self._history:
            last_review = self._history[-1].get("review", "")
            if action.review.strip() == last_review.strip():
                loop_penalty = -0.15

        # Grade the action
        grade = grade_action(
            self._task_id,
            action.review,
            action.issues_found,
        )
        raw_score = grade["score"]

        # Partial progress: reward improves over steps if agent refines review
        step_bonus = 0.0
        if self._history:
            prev_score = self._history[-1].get("score", 0.0)
            if raw_score > prev_score:
                step_bonus = round((raw_score - prev_score) * 0.1, 3)

        final_reward_value = round(
            min(0.999, max(0.001, raw_score + step_bonus + loop_penalty)), 3
        )
        self._cumulative_reward = round(
            min(0.999, self._cumulative_reward + final_reward_value * 0.5), 3
        )

        reward = Reward(
            value=final_reward_value,
            breakdown={
                **grade["breakdown"],
                "step_bonus": step_bonus,
                "loop_penalty": loop_penalty,
            },
            feedback=grade["feedback"],
        )

        # Record history
        self._history.append({
            "step": self._step_count,
            "review": action.review,
            "issues_found": action.issues_found,
            "score": raw_score,
            "reward": final_reward_value,
        })

        # Episode ends when max_steps reached or agent scores >= 0.85
        task = TASKS[self._task_id]
        self._done = (
            self._step_count >= task["max_steps"]
            or final_reward_value >= 0.85
        )

        # Update observation
        self._current_obs = Observation(
            task_id=self._task_id,
            difficulty=task["difficulty"],
            code_snippet=task["code_snippet"],
            language=task["language"],
            instructions=task["instructions"],
            step_count=self._step_count,
            max_steps=task["max_steps"],
            history=copy.deepcopy(self._history),
        )

        return StepResult(
            observation=self._current_obs,
            reward=reward,
            done=self._done,
            info={
                "required_found": grade.get("required_found", []),
                "required_missing": grade.get("required_missing", []),
                "cumulative_reward": self._cumulative_reward,
            },
        )

    def state(self) -> StateResponse:
        """Return current environment state (no side effects)."""
        return StateResponse(
            task_id=self._task_id or "",
            difficulty=TASKS.get(self._task_id, {}).get("difficulty", ""),
            step_count=self._step_count,
            done=self._done,
            cumulative_reward=self._cumulative_reward,
            current_observation=self._current_obs,
        )
