"""
Task definitions and deterministic graders for the Code Review Environment.
Each task has:
  - A code snippet with intentional issues
  - Required keywords the agent must identify to earn score
  - A grader function returning a score 0.0–1.0
"""
from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

TASKS: Dict[str, Dict[str, Any]] = {

    "task_easy": {
        "id": "task_easy",
        "difficulty": "easy",
        "language": "python",
        "instructions": (
            "Review the following Python function. "
            "Identify all bugs, syntax errors, and logical mistakes. "
            "List each issue with the line number and explain how to fix it."
        ),
        "code_snippet": """\
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total =+ num          # line 4: bug here
    average = total / len(numbers)  # line 5: no zero-division guard
    return average

result = calculate_average([10, 20, 30])
print("Average is: " + result)   # line 9: type error
""",
        # Keywords grader checks for (case-insensitive)
        "required_keywords": ["=+", "zero", "division", "str", "type", "concatenat"],
        # Partial credit keywords
        "partial_keywords": ["bug", "error", "fix", "line 4", "line 5", "line 9", "average"],
        "max_steps": 3,
    },

    "task_medium": {
        "id": "task_medium",
        "difficulty": "medium",
        "language": "python",
        "instructions": (
            "Review this Python function that processes user orders. "
            "Find all logic bugs that would cause incorrect behavior at runtime. "
            "Explain each bug clearly and provide the corrected code."
        ),
        "code_snippet": """\
def process_orders(orders):
    \"\"\"Returns total revenue and list of fulfilled orders.\"\"\"
    fulfilled = []
    total_revenue = 0

    for order in orders:
        if order['quantity'] > 0 and order['price'] > 0:
            revenue = order['quantity'] * order['price']
            total_revenue =+ revenue          # line 9: accumulation bug
            if order.get('status') != 'cancelled':
                fulfilled.append(order)

    discount = 0
    if total_revenue > 1000:
        discount = total_revenue * 0.1
    total_revenue = total_revenue - discount  # applied even when revenue resets

    return total_revenue, fulfilled           # line 17: wrong return order docs say (fulfilled, revenue)

def get_order_count(orders):
    count = 0
    for i in range(len(orders)):
        count + 1                             # line 22: count never incremented
    return count
""",
        "required_keywords": ["=+", "accumul", "count", "increment", "discount", "logic"],
        "partial_keywords": ["bug", "line 9", "line 22", "revenue", "+=", "fix", "incorrect"],
        "max_steps": 3,
    },

    "task_very_hard": {
        "id": "task_very_hard",
        "difficulty": "very_hard",
        "language": "python",
        "instructions": (
            "Review this multi-class Python codebase. "
            "Find all cross-class bugs, race conditions, resource leaks, "
            "and design flaws. Explain how each bug manifests at runtime and provide fixes."
        ),
        "code_snippet": """\
import threading
import time

class DatabasePool:
    def __init__(self, size=5):
        self.size = size
        self.connections = []
        self.lock = threading.Lock()
        for _ in range(size):
            self.connections.append({"id": _, "in_use": False})

    def get_connection(self):
        for conn in self.connections:       # line 13: no lock held — race condition
            if not conn["in_use"]:
                conn["in_use"] = True
                return conn
        return None                         # line 17: returns None silently, no error

    def release_connection(self, conn):
        conn["in_use"] = False              # line 20: no lock — race condition


class DataProcessor:
    def __init__(self):
        self.pool = DatabasePool()
        self.results = []

    def process(self, items):
        threads = []
        for item in items:
            t = threading.Thread(target=self._worker, args=(item,))
            threads.append(t)
            t.start()
        # line 34: never joins threads — results may be incomplete
        return self.results

    def _worker(self, item):
        conn = self.pool.get_connection()
        try:
            time.sleep(0.01)
            result = item * 2
            self.results.append(result)     # line 42: list append not thread-safe
        finally:
            if conn:
                self.pool.release_connection(conn)
            # line 45: file handle never opened but pattern shows missing close

    def process_file(self, filepath):
        f = open(filepath, 'r')             # line 48: file never closed — resource leak
        data = f.read()
        return data.split('\\n')
""",
        "required_keywords": [
            "race condition", "lock", "thread-safe", "join", "resource leak",
            "file", "close", "none", "append"
        ],
        "partial_keywords": [
            "threading", "concurrent", "deadlock", "pool", "connection",
            "line 13", "line 20", "line 34", "line 42", "line 48",
            "bug", "fix", "unsafe", "leak"
        ],
        "max_steps": 3,
    },

    "task_expert": {
        "id": "task_expert",
        "difficulty": "expert",
        "language": "python",
        "instructions": (
            "Perform an expert-level performance and correctness review. "
            "Identify all algorithmic inefficiencies (Big-O problems), memory issues, "
            "and correctness bugs. For each issue state the current complexity, "
            "the optimal complexity, and provide the optimized solution."
        ),
        "code_snippet": """\
def find_duplicates(arr):
    \"\"\"Return all duplicate values in the list.\"\"\"
    duplicates = []
    for i in range(len(arr)):               # line 4: O(n²) — should be O(n)
        for j in range(len(arr)):
            if i != j and arr[i] == arr[j]:
                if arr[i] not in duplicates:
                    duplicates.append(arr[i])
    return duplicates


def flatten_nested(nested, result=None):   # line 11: mutable default argument bug
    \"\"\"Flatten a nested list.\"\"\"
    if result is None:
        result = []
    for item in nested:
        if isinstance(item, list):
            flatten_nested(item, result)
        else:
            result.append(item)
    return result


def get_user_data(user_ids):
    \"\"\"Fetch user records for a list of IDs.\"\"\"
    db = connect_to_db()
    results = []
    for uid in user_ids:
        user = db.query(f"SELECT * FROM users WHERE id={uid}")  # line 27: N+1 query problem
        results.append(user)
    return results


def count_words(text):
    \"\"\"Count frequency of each word.\"\"\"
    counts = {}
    words = text.lower().split()
    for word in words:
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1              # line 39: correct but verbose — should use Counter or defaultdict
    word_list = list(counts.items())
    word_list.sort(key=lambda x: x[1])   # line 41: ascending sort — likely wants descending
    return word_list
""",
        "required_keywords": [
            "o(n²)", "o(n)", "set", "n+1", "query", "mutable default",
            "sort", "descending", "complexity", "performance"
        ],
        "partial_keywords": [
            "inefficient", "optimize", "algorithm", "line 4", "line 11", "line 27",
            "line 41", "duplicate", "flatten", "counter", "defaultdict",
            "database", "batch", "fix", "bug"
        ],
        "max_steps": 3,
    },

    "task_hard": {
        "id": "task_hard",
        "difficulty": "hard",
        "language": "python",
        "instructions": (
            "Perform a security-focused code review on this Flask API endpoint. "
            "Identify ALL security vulnerabilities including injection attacks, "
            "authentication issues, data exposure, and insecure practices. "
            "Rate severity (critical/high/medium/low) for each issue and provide fixes."
        ),
        "code_snippet": """\
from flask import Flask, request, jsonify
import sqlite3
import hashlib
import os

app = Flask(__name__)
SECRET_KEY = "hardcoded_secret_123"          # line 7

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Hash password with MD5
    pwd_hash = hashlib.md5(password.encode()).hexdigest()   # line 14: weak hash

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Direct string interpolation — SQL injection
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{pwd_hash}'"  # line 19
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"status": "ok", "user": user})   # line 24: full row exposed
    return jsonify({"status": "fail", "reason": "Invalid credentials"})

@app.route('/admin', methods=['GET'])
def admin_panel():
    user_id = request.args.get('user_id')
    # No authentication check
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id={user_id}")  # line 33: SQL injection
    users = cursor.fetchall()
    conn.close()
    return jsonify({"users": users})                           # line 36: mass data exposure

@app.route('/debug')
def debug():
    return jsonify({
        "env": dict(os.environ),                              # line 40: env vars exposed
        "secret": SECRET_KEY,
    })
""",
        "required_keywords": [
            "sql injection", "md5", "hardcoded", "secret", "authentication",
            "exposure", "parameterized", "bcrypt", "environ"
        ],
        "partial_keywords": [
            "injection", "weak", "hash", "password", "line 7", "line 14", "line 19",
            "line 33", "line 40", "critical", "high", "vulnerability", "secure"
        ],
        "max_steps": 3,
    },
}


# ---------------------------------------------------------------------------
# Graders
# ---------------------------------------------------------------------------

def _keyword_score(text: str, required: List[str], partial: List[str]) -> float:
    """
    Score based on keyword coverage.
    - Each required keyword found: worth (0.6 / len(required)) points
    - Each partial keyword found: worth (0.4 / len(partial)) points
    """
    text_lower = text.lower()

    req_score = sum(1 for kw in required if kw.lower() in text_lower)
    par_score = sum(1 for kw in partial if kw.lower() in text_lower)

    req_ratio = req_score / len(required) if required else 0.0
    par_ratio = par_score / len(partial) if partial else 0.0

    return round(min(1.0, req_ratio * 0.65 + par_ratio * 0.35), 3)


def grade_action(task_id: str, action_text: str, issues_found: List[str]) -> Dict[str, Any]:
    """
    Deterministic grader. Returns score 0.0–1.0 and breakdown.
    """
    task = TASKS.get(task_id)
    if not task:
        return {"score": 0.0, "breakdown": {}, "feedback": "Unknown task."}

    combined_text = action_text + " " + " ".join(issues_found)

    base_score = _keyword_score(
        combined_text,
        task["required_keywords"],
        task["partial_keywords"],
    )

    # Penalize very short / low-effort reviews
    word_count = len(combined_text.split())
    if word_count < 20:
        base_score *= 0.3
        length_penalty = -0.7
    elif word_count < 50:
        base_score *= 0.7
        length_penalty = -0.3
    else:
        length_penalty = 0.0

    # Bonus: agent provided a suggested fix
    fix_bonus = 0.05 if "fix" in combined_text.lower() or "suggest" in combined_text.lower() else 0.0

    final_score = round(min(1.0, max(0.0, base_score + fix_bonus)), 3)

    req_found = [kw for kw in task["required_keywords"] if kw.lower() in combined_text.lower()]
    req_missing = [kw for kw in task["required_keywords"] if kw.lower() not in combined_text.lower()]

    feedback_parts = []
    if req_found:
        feedback_parts.append(f"Correctly identified: {', '.join(req_found)}.")
    if req_missing:
        feedback_parts.append(f"Missed key issues: {', '.join(req_missing)}.")
    if length_penalty < 0:
        feedback_parts.append("Review was too brief — provide more detail.")
    if fix_bonus > 0:
        feedback_parts.append("Good — you included fix suggestions.")

    return {
        "score": final_score,
        "breakdown": {
            "keyword_score": base_score,
            "length_penalty": length_penalty,
            "fix_bonus": fix_bonus,
        },
        "feedback": " ".join(feedback_parts) or "Review processed.",
        "required_found": req_found,
        "required_missing": req_missing,
    }
