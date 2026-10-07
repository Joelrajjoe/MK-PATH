import json
from pathlib import Path
import pandas as pd
import duckdb

BASE_DIR = Path(r"E:\MKPATH")
RUN_ID = "e2e-20261007-064600"
EVIDENCE_DIR = BASE_DIR / "_e2e_validation" / RUN_ID / "evidence"

source_csv_path = Path(r"E:\MKPATH\datasets\53a3d79cb8454309afd46b9880df8f08\Superstore sales dataset.csv")
raw_df = pd.read_csv(source_csv_path, encoding="utf-8", encoding_errors="replace")

# Setup DuckDB query directly on normalized parquet
parquet_path = Path(r"E:\MKPATH\data\53a3d79cb8454309afd46b9880df8f08\3f14e39397b045e3b00a0bd973a4162f.parquet").as_posix()
conn = duckdb.connect()

metrics = ["Sales", "Quantity", "Profit", "Discount"]
kpi_comparison = {}

for m in metrics:
    q = f'SELECT SUM("{m}") as sum_val, AVG("{m}") as avg_val, MIN("{m}") as min_val, MAX("{m}") as max_val FROM read_parquet(\'{parquet_path}\')'
    duck_res = conn.execute(q).df().to_dict(orient="records")[0]
    
    s = raw_df[m].dropna()
    ind_sum = float(s.sum())
    ind_avg = float(s.mean())
    ind_min = float(s.min())
    ind_max = float(s.max())
    
    sys_sum = float(duck_res["sum_val"])
    sys_avg = float(duck_res["avg_val"])
    sys_min = float(duck_res["min_val"])
    sys_max = float(duck_res["max_val"])
    
    diff_sum = abs(sys_sum - ind_sum)
    diff_avg = abs(sys_avg - ind_avg)
    
    kpi_comparison[m] = {
        "system_sum": sys_sum,
        "ind_sum": ind_sum,
        "diff_sum": diff_sum,
        "system_avg": sys_avg,
        "ind_avg": ind_avg,
        "diff_avg": diff_avg,
        "system_min": sys_min,
        "ind_min": ind_min,
        "system_max": sys_max,
        "ind_max": ind_max,
        "tolerance": 1e-4,
        "status": "PASS" if diff_sum < 1e-4 and diff_avg < 1e-4 else "FAIL"
    }

with open(EVIDENCE_DIR / "a8_kpi_comparison.json", "w", encoding="utf-8") as f:
    json.dump(kpi_comparison, f, indent=2)

print("KPI Recomputation Results:")
for m, v in kpi_comparison.items():
    print(f" - {m}: System SUM={v['system_sum']:.2f}, Ind SUM={v['ind_sum']:.2f}, diff={v['diff_sum']:.6f} => {v['status']}")
