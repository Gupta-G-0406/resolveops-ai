import os
import subprocess
import sys
import time

env = os.environ.copy()
env["HF_HUB_OFFLINE"] = "1"
env["TRANSFORMERS_OFFLINE"] = "1"

code = """
from app.rag.policy_store import search_policies
results = search_policies("Delivered but not received", limit=3)
print([p["policy_id"] for p in results], flush=True)
"""

started = time.perf_counter()

try:
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        timeout=120,
    )

    print("Exit code:", result.returncode)
    print("Elapsed:", round(time.perf_counter() - started, 2))
    print("Output:", result.stdout)

except subprocess.TimeoutExpired:
    print("Subprocess timed out after 120 seconds")