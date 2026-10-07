import os
import shutil
import json
from pathlib import Path

ROOT_DIR = Path(r"E:\MKPATH")
DATA_DIR = ROOT_DIR / "data"
DATASETS_DIR = ROOT_DIR / "datasets"
MODELS_DIR = ROOT_DIR / "models"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
METADATA_DIR = DATA_DIR / "metadata"

print("Starting clean reset of MK-Path workspace...")

# 1. Reset all metadata JSON collections
METADATA_DIR.mkdir(parents=True, exist_ok=True)
collections = [
    "projects", "datasets", "ontology", "agent_runs", "runs",
    "clarification_questions", "human_decisions", "validation_results",
    "models", "artifacts", "audit_events", "healing_events"
]
for col in collections:
    file_path = METADATA_DIR / f"{col}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("[]")
    print(f"  Reset {col}.json -> []")

# 2. Clear all dataset storage subdirectories in data/ (except metadata)
if DATA_DIR.exists():
    for item in DATA_DIR.iterdir():
        if item.is_dir() and item.name != "metadata":
            try:
                shutil.rmtree(item)
            except Exception as e:
                print(f"  Warning removing {item.name}: {e}")
print("  Cleared data/ upload directories.")

# 3. Clear all datasets/ subdirectories
if DATASETS_DIR.exists():
    for item in DATASETS_DIR.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception as e:
            print(f"  Warning removing {item.name}: {e}")
print("  Cleared datasets/ directories.")

# 4. Clear models and artifacts
for folder in [MODELS_DIR, ARTIFACTS_DIR]:
    if folder.exists():
        for item in folder.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception as e:
                pass
print("  Cleared models/ and artifacts/ directories.")

print("Clean reset completed successfully!")
