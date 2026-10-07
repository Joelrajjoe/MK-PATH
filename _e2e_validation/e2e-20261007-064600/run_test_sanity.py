import subprocess
import json
from pathlib import Path

BASE_DIR = Path(r"E:\MKPATH")
RUN_ID = "e2e-20261007-064600"
EVIDENCE_DIR = BASE_DIR / "_e2e_validation" / RUN_ID / "evidence"

tests = [
    "tests/test_projects.py",
    "tests/test_remediation.py",
    "tests/test_profiling.py",
    "tests/test_ingestion.py"
]

results = {}
for t in tests:
    cmd = [r"E:\MKPATH\backend\.venv\Scripts\pytest", t, "-q"]
    proc = subprocess.run(cmd, cwd=str(BASE_DIR / "backend"), capture_output=True, text=True)
    results[t] = {
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "status": "PASS" if proc.returncode == 0 else "FAIL"
    }

with open(EVIDENCE_DIR / "b3_test_sanity.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("Test-suite sanity complete:")
for t, r in results.items():
    print(f" - {t}: {r['status']} (code {r['exit_code']})")
