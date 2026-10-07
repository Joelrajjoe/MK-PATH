import os
import re
import json
import subprocess
from pathlib import Path

RUN_ID = "e2e-20261007-064600"
BASE_DIR = Path(r"E:\MKPATH")
OUT_DIR = BASE_DIR / "_e2e_validation" / RUN_ID / "evidence"
OUT_DIR.mkdir(parents=True, exist_ok=True)

patterns = [
    r"\bmock\b", r"\bdummy\b", r"\bfake\b", r"\bplaceholder\b",
    r"\bhardcoded\b", r"\bdemo\b", r"\bsample_data\b", r"\blorem\b",
    r"\bTODO\b", r"\bFIXME\b", r"setTimeout", r"Math\.random",
    r"random\.(rand|choice|randint)",
    r"(accuracy|auc|f1|precision|recall|quality|score|confidence)\s*[:=]\s*0?\.\d+"
]

regex = re.compile("|".join(patterns), re.IGNORECASE)

findings = []
skip_dirs = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", "_e2e_validation"}
extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}

for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for file in files:
        fpath = Path(root) / file
        if fpath.suffix in extensions:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(content.splitlines(), start=1):
                    m = regex.search(line)
                    if m:
                        rel = fpath.relative_to(BASE_DIR).as_posix()
                        # Categorize
                        category = "PRODUCTION_HARDCODE"
                        if "test" in rel.lower():
                            category = "LEGITIMATE_TEST"
                        elif "doc" in rel.lower() or line.strip().startswith("#") or line.strip().startswith("//"):
                            category = "DOCUMENTATION"
                        elif "TODO" in line or "FIXME" in line:
                            category = "DOCUMENTATION"
                        elif "config" in rel.lower():
                            category = "LEGITIMATE_CONFIG"
                        elif "mock" in m.group(0).lower() or "fake" in m.group(0).lower():
                            category = "PRODUCTION_MOCK"
                        
                        findings.append({
                            "file": rel,
                            "line": idx,
                            "match": m.group(0),
                            "content": line.strip()[:140],
                            "category": category
                        })
            except Exception as e:
                pass

with open(OUT_DIR / "b1_mock_audit.json", "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

print(f"B1 audit complete. Total findings: {len(findings)}")
cats = {}
for item in findings:
    cats[item["category"]] = cats.get(item["category"], 0) + 1
print("Categories:", cats)
