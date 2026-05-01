# วิธีรันโปรเจกต์ Gold Safe Haven (เครื่องใหม่)

## ขั้นตอนที่ 1: ติดตั้ง Python

- ดาวน์โหลด Python 3.11+ จาก https://www.python.org/downloads/
- ตอนติดตั้ง **ติ๊ก "Add Python to PATH"**
- ตรวจสอบ: เปิด Terminal พิมพ์ `py --version`

## ขั้นตอนที่ 2: ติดตั้ง Java (สำหรับ PySpark)

- แนะนำ **JDK 17** หรือ **JDK 11** จาก https://adoptium.net/
- ตั้ง Environment Variable `JAVA_HOME` ชี้ไปโฟลเดอร์ JDK
- ไม่แนะนำ Java 23 กับ Spark บน Windows เพราะอาจเจอ error `getSubject is supported only if a security manager is allowed`
- ถ้า Spark ใช้ไม่ได้ → pipeline จะ fallback/ข้ามส่วน Spark ที่เขียน Parquet partition แต่ส่วน dashboard-ready และ ML ยังรันต่อได้

## ขั้นตอนที่ 3: ติดตั้ง Library

เปิด Terminal แล้ว cd เข้าโฟลเดอร์โปรเจกต์:
## ชื่อโฟลเดอร์ต้องถูกต้อง
```bash
cd "C:\Users\Moji\Desktop\Finalbigdata\gold-safe-haven-bigdata"
pip install -r requirements.txt
```

> **สำคัญ**: ต้องอยู่ในโฟลเดอร์ `gold-safe-haven-bigdata` ที่มีไฟล์ `requirements.txt`
> Airflow ไม่อยู่ใน requirements หลักแล้วเพื่อให้ Windows venv ติดตั้งง่ายขึ้น ใช้ Docker Compose สำหรับ Airflow หรือดู `requirements-airflow.txt`

## ขั้นตอนที่ 4: รัน Pipeline (ดึงข้อมูล + วิเคราะห์)

```bash
py run_pipeline.py
```

Pipeline จะรันตามลำดับ:
1. `ingest_yahoo.py` — ดึงราคาสินทรัพย์จาก Yahoo Finance (~35 ตัว)
2. `ingest_fred.py` — ดึงข้อมูลมหภาคจาก FRED (VIX, USREC, Fed Rate ฯลฯ)
3. `validate_data.py` — ตรวจสอบคุณภาพ raw data
4. `clean_integrate.py` — ทำความสะอาด + รวมข้อมูลเป็น master panel
5. `spark_process.py` — Parquet partition + CSV vs Parquet benchmark
6. `feature_engineering.py` — สร้าง features (return, drawdown, rolling vol, correlation)
7. `crisis_labeling.py` — label วิกฤต (VIX>30, recession, SPY drawdown)
8. `spark_transform.py` — **PySpark Transformation Layer** (Safe Haven Score, Market Breadth, สถิติสรุป)
9. `modeling.py` — ML benchmark (LogReg, RF, XGBoost) ด้วย TimeSeriesSplit + sklearn Pipeline (`SimpleImputer → StandardScaler → Model`) และ lag-1 features เพื่อลด leakage
10. `generate_dashboard_data.py` — เตรียมไฟล์สำหรับ Dashboard

หลังขั้นตอนนี้ควรมี `data/dashboard/analysis_panel.parquet` ซึ่งเป็น processed/dashboard-ready panel สำหรับให้ Streamlit ใช้ทำ Time Filter, Asset Filter และ Rolling Window โดย Dashboard จะไม่อ่าน raw data โดยตรง

> ใช้เวลาประมาณ **2-5 นาที** (ขึ้นกับอินเทอร์เน็ตตอนดึงข้อมูล)

## ขั้นตอนที่ 5: เปิด Dashboard

```bash
py -m streamlit run app/dashboard.py
```

จะเปิดหน้าเว็บอัตโนมัติที่ **http://localhost:8501**

## สรุปคำสั่งทั้งหมด (copy-paste ได้เลย)

```bash
cd "C:\path\to\gold-safe-haven-bigdata"
pip install -r requirements.txt
py run_pipeline.py
py -m streamlit run app/dashboard.py
```

## โครงสร้างโฟลเดอร์หลัง Pipeline รัน

```
gold-safe-haven-bigdata/
├── app/dashboard.py          ← Streamlit Dashboard
├── src/                      ← โค้ด Pipeline ทั้งหมด
│   ├── ingest_yahoo.py
│   ├── ingest_fred.py
│   ├── validate_data.py
│   ├── clean_integrate.py
│   ├── spark_process.py
│   ├── feature_engineering.py
│   ├── crisis_labeling.py
│   ├── spark_transform.py    ← PySpark Transformation Layer (ใหม่)
│   ├── modeling.py
│   └── generate_dashboard_data.py
├── data/
│   ├── raw/                  ← ข้อมูลดิบ (Yahoo + FRED CSV)
│   ├── cleaned/              ← ข้อมูลหลัง clean
│   ├── integrated/           ← master panel + feature + labeled datasets
│   ├── spark_output/         ← output จาก spark_transform (สถิติสรุป)
│   └── dashboard/            ← ไฟล์ที่ Dashboard อ่าน (processed only)
│       └── analysis_panel.parquet ← ฐานข้อมูลกลางสำหรับ interactive filters
├── reports/                  ← สรุปผล + benchmark
├── dags/                     ← Airflow DAG
├── run_pipeline.py           ← รัน pipeline ทั้งหมด
└── requirements.txt
```

## หมายเหตุ

- **Spark ไม่พร้อม?** → ไม่เป็นไร pipeline จะ fallback ใช้ Pandas แทนและยังทำงานได้ครบ
- **Yahoo/FRED โหลดไม่ได้?** → ถ้ามีไฟล์ raw เดิม pipeline จะใช้ cached raw data ต่อและ log เป็น `USING_CACHED`
- **XAUUSD=X fail?** → ปกติ ticker นี้ถูก delist แล้ว ใช้ GC=F (Gold Futures) แทน และ log เป็น optional failure
- **Airflow** → ใช้สำหรับ orchestration เท่านั้น ไม่จำเป็นต้องติดตั้งเพื่อรัน pipeline
- **Return Ranking vs Safe Haven Ranking** → แยกแล้ว: `return_ranking.csv` ใช้ mean crisis return เท่านั้น ส่วน `safe_haven_ranking.csv` ใช้ composite score 6 มิติ

## ภาคผนวก

- `docs/AI_COLLABORATION_LOG.md` — ตัวอย่างคำถาม/Prompt ที่ใช้ร่วมกับ AI ในการพัฒนาโครงงาน
