# Final Insights (สรุปสำหรับรายงาน)

## 1) Multi-source data
- ใช้ Yahoo (หลายสินทรัพย์) + FRED (macro/stress) เพื่อเพิ่ม variety และตอบคำถาม **WHY**

## 2) PySpark Transformation Layer
- spark_transform.py สร้างสถิติสรุป, Safe Haven Score, Market Breadth, Return Ranking
- Dashboard อ่านเฉพาะ processed data จาก data/dashboard/ ไม่อ่าน raw data

## 3) Airflow
- Airflow orchestrate pipeline แบบ repeatable และตรวจสอบสถานะแต่ละขั้นได้

## 4) Parquet
- Parquet อ่านเร็ว บีบอัดดี เหมาะกับข้อมูลขนาดใหญ่และ Spark

## 5) Safe Haven Score
- ใช้ composite score 6 มิติ (return, outperform, drawdown, vol, corr, hit rate)
- แยกชัดจาก Return Ranking — mean return ≠ safe haven

## 6) Key insight
- ทองเป็น **conditional safe haven** — ดีในบางวิกฤต ล้มเหลวในบางช่วง
