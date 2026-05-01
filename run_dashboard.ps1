# รัน Streamlit จากโฟลเดอร์โปรเจกต์ (รองรับ path ที่มีวงเล็บ)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "ไม่พบ $Py — สร้าง venv และ pip install -r requirements.txt ก่อน" -ForegroundColor Red
    exit 1
}
& $Py -m streamlit run (Join-Path $Root "app\dashboard.py")
