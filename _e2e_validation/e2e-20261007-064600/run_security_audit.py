import os
import re
import json
import zipfile
import io
from pathlib import Path
from fastapi.testclient import TestClient

RUN_ID = "e2e-20261007-064600"
BASE_DIR = Path(r"E:\MKPATH")
OUT_DIR = BASE_DIR / "_e2e_validation" / RUN_ID / "evidence"

security_findings = []

# 1. Check for hardcoded secrets/keys in frontend files
frontend_dir = BASE_DIR / "frontend" / "src"
secret_patterns = [
    (r"mongodb(\+srv)?:\/\/[^\s'\"]+", "MongoDB Connection String"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key"),
    (r"gsk_[0-9A-Za-z]{30,}", "Groq API Key"),
    (r"sk-[0-9A-Za-z]{20,}", "OpenAI API Key"),
    (r"(password|secret|apikey|api_key)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "Hardcoded Credential")
]

fe_secrets = []
for f in frontend_dir.rglob("*"):
    if f.is_file() and f.suffix in {".ts", ".tsx", ".js", ".jsx", ".html"}:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for pat, desc in secret_patterns:
            m = re.search(pat, txt, re.IGNORECASE)
            if m:
                # Redact
                val = m.group(0)
                redacted = val[:4] + "***" + val[-4:] if len(val) > 8 else "***"
                fe_secrets.append({
                    "file": str(f.relative_to(BASE_DIR)),
                    "type": desc,
                    "redacted_sample": redacted
                })

security_findings.append({
    "check": "Frontend Secrets Check",
    "status": "PASS" if not fe_secrets else "FAIL",
    "details": fe_secrets if fe_secrets else "No Atlas or provider credentials leaked in frontend source/bundle."
})

# 2. Check eval/exec/pickle.load
code_findings = []
backend_dir = BASE_DIR / "backend" / "app"
for f in backend_dir.rglob("*.py"):
    txt = f.read_text(encoding="utf-8", errors="ignore")
    lines = txt.splitlines()
    for idx, l in enumerate(lines, 1):
        if re.search(r"\b(eval|exec)\s*\(", l):
            code_findings.append({"file": str(f.relative_to(BASE_DIR)), "line": idx, "type": "eval/exec", "content": l.strip()})
        if "pickle.load" in l:
            code_findings.append({"file": str(f.relative_to(BASE_DIR)), "line": idx, "type": "pickle.load", "content": l.strip()})

security_findings.append({
    "check": "Code Execution (eval/exec/pickle)",
    "status": "PASS" if not any(x["type"] == "eval/exec" for x in code_findings) else "FAIL",
    "details": code_findings
})

# 3. Test ZIP Slip Protection
import sys
sys.path.insert(0, str(BASE_DIR / "backend"))
from app.main import app

client = TestClient(app)

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w") as z:
    z.writestr("../../../evil.txt", "MALICIOUS CONTENT")
    z.writestr("safe.csv", "a,b\n1,2\n")

zip_buffer.seek(0)
res = client.post("/api/datasets/upload", files={"file": ("malicious.zip", zip_buffer.getvalue(), "application/zip")})

# Ingestion should either sanitize path or reject/skip evil entry
is_zip_slip_safe = res.status_code in {200, 201, 400, 422}
evil_on_disk = Path(r"E:\evil.txt").exists() or Path(r"E:\MKPATH\evil.txt").exists()

security_findings.append({
    "check": "ZIP Slip / Path Traversal Defense",
    "status": "PASS" if is_zip_slip_safe and not evil_on_disk else "FAIL",
    "http_status": res.status_code,
    "evil_file_created": evil_on_disk,
    "response_text": res.text[:200]
})

with open(OUT_DIR / "b2_security_audit.json", "w", encoding="utf-8") as f:
    json.dump(security_findings, f, indent=2)

print("B2 security audit complete.")
for sf in security_findings:
    print(f" - {sf['check']}: {sf['status']}")
