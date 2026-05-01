# AI Collaboration / Prompt Engineering Log

ภาคผนวกนี้สรุปตัวอย่างคำถามและ prompt ที่ใช้ร่วมกับ Generative AI ระหว่างพัฒนาโปรเจกต์  
เป้าหมายไม่ใช่ให้ AI ทำงานแทนทั้งหมด แต่ใช้เป็นผู้ช่วยด้านการออกแบบสถาปัตยกรรม ตรวจ logic, debug, ปรับ dashboard และเตรียมเอกสารให้สอดคล้องกับ rubric ของรายวิชา

## 1. Project Architecture and Scope

**Prompt / Question**

> ช่วยออกแบบโครงสร้างโปรเจกต์ Big Data สำหรับวิเคราะห์ว่าทองคำเป็น safe haven จริงหรือไม่ โดยใช้ Yahoo Finance, FRED, Airflow, Spark, Machine Learning และ Streamlit Dashboard

**Purpose**

กำหนดภาพรวมของระบบให้เป็น end-to-end pipeline ตั้งแต่ ingestion จนถึง dashboard-ready data

**Outcome**

ได้ architecture หลัก: Yahoo Finance + FRED → Airflow DAG → Ingestion → Validation → Cleaning/Integration → Spark/Parquet → Feature Engineering → Crisis Labeling → ML Benchmark → Dashboard Data → Streamlit Dashboard

## 2. Pipeline Execution Order

**Prompt / Question**

> ช่วยตรวจว่าควรรันไฟล์ไหนก่อนหลังในโปรเจกต์นี้ และแต่ละขั้นตอนควรสร้าง output อะไรบ้าง

**Purpose**

ป้องกันปัญหารันผิดลำดับและทำให้ pipeline อธิบายได้ชัดเจนในการนำเสนอ

**Outcome**

ได้ลำดับงานที่สอดคล้องกับ `run_pipeline.py` และ Airflow DAG รวมถึงระบุ output เช่น raw CSV, integrated parquet, spark output, reports และ dashboard-ready files

## 3. Data Ingestion Robustness

**Prompt / Question**

> ช่วยทำให้ ingestion จาก Yahoo Finance และ FRED ทนต่อ API error ได้ เช่น ถ้าเน็ตล่มหรือ ticker บางตัวโหลดไม่ได้ ให้ใช้ cached data ต่อได้

**Purpose**

ทำให้ pipeline รันซ้ำได้จริง ไม่ล้มทั้งระบบจาก external API เพียงจุดเดียว

**Outcome**

เพิ่มแนวคิด cached fallback, logging สถานะ download และจัดการ optional ticker failure เช่น XAUUSD

## 4. Data Validation and Cleaning

**Prompt / Question**

> ช่วยตรวจว่าข้อมูลราคาสินทรัพย์และ macro data ควรถูก validate และ clean อย่างไร ก่อนรวมเป็น master panel

**Purpose**

เพิ่มความน่าเชื่อถือของข้อมูลก่อนนำไปวิเคราะห์

**Outcome**

มีขั้นตอนตรวจ missing values, duplicates, date range, asset coverage และรวมข้อมูลด้วย date alignment / forward-fill ตามบริบทของ financial time series

## 5. Parquet and Spark Layer

**Prompt / Question**

> ช่วยเพิ่มชั้น PySpark transformation/statistics layer และทำ Parquet output เพื่อให้โปรเจกต์มีองค์ประกอบ Big Data ชัดเจน

**Purpose**

ให้โปรเจกต์ไม่ใช่แค่ pandas analysis แต่มี storage/processing layer ที่เหมาะกับ Big Data pipeline

**Outcome**

มี `spark_process.py` สำหรับ Parquet/benchmark และ `spark_transform.py` สำหรับสร้าง statistics, market breadth, risk detail, rolling correlation และ safe haven score

## 6. Crisis Labeling Methodology

**Prompt / Question**

> ช่วยออกแบบวิธี label ช่วงวิกฤตให้ไม่พึ่งตัวแปรเดียว โดยใช้ VIX, recession flag และ SPY drawdown

**Outcome**

ได้ crisis labeling ที่รวมหลายเงื่อนไข เช่น VIX stress, NBER recession และ equity drawdown

## 7. Machine Learning Preprocessing

**Prompt / Question**

> โปรเจกต์นี้มี preprocessing ของ Machine Learning ใน scikit-learn แล้วหรือยัง ช่วยเพิ่มให้ถูกต้องถ้ายังไม่ครบ

**Purpose**

ป้องกัน data leakage และทำให้ ML benchmark ดูเป็นระบบมากขึ้น

**Outcome**

เพิ่มแนวคิด `sklearn Pipeline` เช่น `SimpleImputer → StandardScaler → Model`, ใช้ lag-1 features และ `TimeSeriesSplit` เพื่อเหมาะกับ time-series data

## 8. Return Ranking vs Safe Haven Ranking

**Prompt / Question**

> ช่วยแยก Return Ranking ออกจาก Safe Haven Ranking เพราะอาจารย์ต้องการให้แยกชัดเจน

**Purpose**

ป้องกันการตีความผิดว่า asset ที่ return สูงสุดคือ safe haven ที่ดีที่สุดเสมอ

**Outcome**

Return Ranking ใช้ mean crisis return ส่วน Safe Haven Ranking ใช้ composite score หลายมิติ เช่น return, outperform SPY, drawdown, volatility, correlation และ hit rate

## 9. Dashboard Data Contract

**Prompt / Question**

> Dashboard ต้องไม่อ่าน raw data ตรง ๆ ช่วยทำให้ dashboard อ่านเฉพาะ processed/dashboard-ready data เท่านั้น

**Purpose**

แยกชั้น data engineering ออกจาก visualization และทำให้ dashboard reproducible

**Outcome**

เพิ่ม `data/dashboard/analysis_panel.parquet` เป็น processed panel สำหรับ Streamlit และใช้ summary CSV/Parquet จาก `data/dashboard/` เท่านั้น

## 10. Interactive Time Filter

**Prompt / Question**

> เพิ่ม Time Filter / Period Selector ใน Streamlit Dashboard ให้ผู้ใช้เลือกช่วงเวลาเองได้ เช่น All Data, Dot-com Crash, 2008 GFC, COVID Crash, 2022 Rate Shock และ Custom Range

**Purpose**

ตอบ requirement ว่าผลลัพธ์ต้องเปลี่ยนตามช่วงเวลา ไม่ใช่แสดงค่า fixed period เดียว

**Outcome**

เพิ่ม global sidebar controls: preset period, custom date range, rolling window 30/90/180 วัน และ asset selector แบบเลือกหลายตัว

## 11. Dashboard Analysis Correctness

**Prompt / Question**

> ช่วยทำให้ทุก chart และ table ใน Overview, Crisis Analysis, Rolling Correlation, Risk, Return Ranking และ Safe Haven Leaderboard update ตาม filter เดียวกัน

**Purpose**

ทำให้ dashboard เป็น interactive analytics จริง ไม่ใช่ static report

**Outcome**

Dashboard pages หลักใช้ shared filtering logic และ recompute metrics ตาม date range, rolling window และ selected assets

## 12. Airflow DAG Debugging

**Prompt / Question**

> ตอนนี้ Airflow DAG task สุดท้าย generate_dashboard_data error ช่วยดู log และแก้ให้รันผ่าน

**Purpose**

แก้ production-like orchestration issue ที่เกิดเฉพาะใน Docker/Airflow runtime

**Outcome**

พบว่า Docker bind mount บน Windows ไม่อนุญาตให้ `shutil.copy2` preserve metadata จึงเปลี่ยนเป็น `shutil.copyfile` และ rerun task สำเร็จ


**Purpose**

ให้ผู้ตรวจเปิด repo แล้วเข้าใจ project, pipeline, how to run และ evidence ตาม rubric ได้ทันที

**Outcome**

ปรับ README, HOW_TO_RUN, `.gitignore` และเพิ่มเอกสารใน `docs/` สำหรับ rubric evidence, public repo checklist และ submission checklist
