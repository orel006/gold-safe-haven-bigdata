"""
รัน pipeline ทั้งหมดตามลำดับ (manual orchestration)
ใช้เมื่อยังไม่ติดตั้ง Airflow
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    "ingest_yahoo.py",
    "ingest_fred.py",
    "validate_data.py",
    "clean_integrate.py",
    "spark_process.py",
    "feature_engineering.py",
    "crisis_labeling.py",
    "spark_transform.py",
    "modeling.py",
    "generate_dashboard_data.py",
]


def main() -> None:
    for script in STEPS:
        print(f"\n>>> Running {script} ...")
        subprocess.check_call([sys.executable, str(ROOT / "src" / script)], cwd=str(ROOT))
    print("\n>>> Pipeline เสร็จสมบูรณ์")


if __name__ == "__main__":
    main()
