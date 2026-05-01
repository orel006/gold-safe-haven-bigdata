"""
Airflow DAG — orchestration ของ Gold Safe Haven pipeline

หมายเหตุ:
- Airflow ใช้จัด **ลำดับงานและ monitoring** ไม่ใช่ engine ประมวลผลหลัก
- แต่ละ task เรียกสคริปต์ Python ในโฟลเดอร์ src/ (รันได้บน Windows ผ่าน PythonOperator)
- ติดตั้ง: pip install apache-airflow แล้วตั้งค่า AIRFLOW_HOME / วางโฟลเดอร์ dags ให้ Airflow มองเห็น

คำสั่ง trigger (หลังตั้งค่า Airflow แล้ว):
  airflow dags trigger gold_safe_haven_pipeline
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# รากโปรเจกต์ = parent ของโฟลเดอร์ dags/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / "src" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"ไม่พบ {script_path}")
    subprocess.check_call([sys.executable, str(script_path)], cwd=str(PROJECT_ROOT))


default_args = {
    "owner": "gold_safe_haven",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="gold_safe_haven_pipeline",
    default_args=default_args,
    description="Gold Safe Haven — Big Data pipeline (Yahoo + FRED → Parquet → ML → Dashboard)",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["gold", "safe_haven", "big_data"],
) as dag:
    t_ingest_yahoo = PythonOperator(
        task_id="ingest_yahoo_data",
        python_callable=_run_script,
        op_args=["ingest_yahoo.py"],
    )
    t_ingest_fred = PythonOperator(
        task_id="ingest_fred_data",
        python_callable=_run_script,
        op_args=["ingest_fred.py"],
    )
    t_validate = PythonOperator(
        task_id="validate_raw_data",
        python_callable=_run_script,
        op_args=["validate_data.py"],
    )
    t_clean = PythonOperator(
        task_id="clean_integrate_data",
        python_callable=_run_script,
        op_args=["clean_integrate.py"],
    )
    t_spark = PythonOperator(
        task_id="spark_process_and_parquet",
        python_callable=_run_script,
        op_args=["spark_process.py"],
    )
    t_feat = PythonOperator(
        task_id="feature_engineering",
        python_callable=_run_script,
        op_args=["feature_engineering.py"],
    )
    t_crisis = PythonOperator(
        task_id="crisis_labeling",
        python_callable=_run_script,
        op_args=["crisis_labeling.py"],
    )
    t_spark_transform = PythonOperator(
        task_id="spark_transform_statistics",
        python_callable=_run_script,
        op_args=["spark_transform.py"],
    )
    t_model = PythonOperator(
        task_id="modeling",
        python_callable=_run_script,
        op_args=["modeling.py"],
    )
    t_dash = PythonOperator(
        task_id="generate_dashboard_data",
        python_callable=_run_script,
        op_args=["generate_dashboard_data.py"],
    )

    t_ingest_yahoo >> t_ingest_fred >> t_validate >> t_clean >> t_spark >> t_feat >> t_crisis >> t_spark_transform >> t_model >> t_dash
