"""
Apache Spark — อ่าน master panel, partition Parquet, benchmark CSV vs Parquet

หมายเหตุ:
- ต้องมี Java + PySpark ติดตั้งแล้ว ถ้า Spark ใช้ไม่ได้ สคริปต์จะบันทึก benchmark ว่า Spark ถูกข้าม
- Parquet เหมาะกับ Big Data: columnar storage, compression, predicate pushdown / partition pruning
"""
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from src.config import PATH_DATA_INTEGRATED, PATH_DATA_PARQUET, PATH_REPORTS, ensure_all_directories


def _dir_size_mb(path: Path) -> float:
    total = 0
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total / (1024 * 1024)


def run_spark_process() -> None:
    ensure_all_directories()
    PATH_REPORTS.mkdir(parents=True, exist_ok=True)

    master_csv = PATH_DATA_INTEGRATED / "master_asset_panel.csv"
    master_pq = PATH_DATA_INTEGRATED / "master_asset_panel.parquet"
    if not master_csv.exists() and not master_pq.exists():
        raise FileNotFoundError("ไม่พบ master_asset_panel — รัน clean_integrate ก่อน")

    # Benchmark ด้วย Pandas (baseline) — เปรียบเทียบ CSV vs Parquet
    t0 = time.perf_counter()
    if master_csv.exists():
        _ = pd.read_csv(master_csv)
    t_csv = time.perf_counter() - t0

    t0 = time.perf_counter()
    if master_pq.exists():
        _ = pd.read_parquet(master_pq)
    t_pq = time.perf_counter() - t0

    csv_mb = _dir_size_mb(master_csv) if master_csv.exists() else 0.0
    pq_mb = _dir_size_mb(master_pq) if master_pq.exists() else 0.0

    spark_status = "SKIPPED"
    spark_partition_sec = None

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F

        spark_status = "OK"
        spark = (
            SparkSession.builder.appName("GoldSafeHaven")
            .master("local[*]")
            .config("spark.sql.shuffle.partitions", "8")
            .getOrCreate()
        )

        read_path = str(master_pq) if master_pq.exists() else str(master_csv)
        if master_pq.exists():
            sdf = spark.read.parquet(read_path)
        else:
            sdf = spark.read.option("header", True).csv(read_path)

        for name in ["date", "Date"]:
            if name in sdf.columns:
                sdf = sdf.withColumnRenamed(name, "date")
                break
        sdf = sdf.withColumn("date", F.to_date(F.col("date")))
        sdf = sdf.withColumn("year", F.year("date")).withColumn("month", F.month("date"))

        out_dir = PATH_DATA_PARQUET / "asset_prices"
        if out_dir.exists():
            import shutil

            shutil.rmtree(out_dir, ignore_errors=True)

        t0 = time.perf_counter()
        sdf.write.partitionBy("group", "asset", "year").parquet(str(out_dir), mode="overwrite")
        spark_partition_sec = time.perf_counter() - t0

        spark.stop()
    except Exception as e:
        spark_status = f"FAILED: {e}"
        print(f"[spark_process] Spark ไม่พร้อมใช้งาน: {e}")
        print("[spark_process] ถ้าใช้ Windows/Java 23 ให้ติดตั้ง JDK 17 หรือ JDK 11 แล้วตั้ง JAVA_HOME ก่อนรัน Spark อีกครั้ง")

    bench = pd.DataFrame(
        [
            {"metric": "pandas_read_csv_sec", "value": round(t_csv, 4)},
            {"metric": "pandas_read_parquet_sec", "value": round(t_pq, 4)},
            {"metric": "master_csv_size_mb", "value": round(csv_mb, 4)},
            {"metric": "master_parquet_size_mb", "value": round(pq_mb, 4)},
            {"metric": "spark_status", "value": spark_status},
            {"metric": "spark_partition_write_sec", "value": spark_partition_sec or 0},
        ]
    )
    bench.to_csv(PATH_REPORTS / "storage_benchmark.csv", index=False, encoding="utf-8-sig")
    print(f"[spark_process] บันทึก {PATH_REPORTS / 'storage_benchmark.csv'}")
    print(bench.to_string(index=False))


if __name__ == "__main__":
    run_spark_process()
