# 🚀 Ishga tushirish — Qadamma-qadam

## 1. O'rnatish

```bash
# Kutubxonalar
pip install -r requirements.txt

# Playwright Chromium brauzeri (bir marta)
playwright install chromium
```

## 2. CLI orqali ishga tushirish

```bash
# Oddiy (headed — brauzer ko'rinadi)
python main.py --no-headless --query "you tube"

# Headless (brauzer yashirin)
python main.py --query "you tube"

# Parallel (3x tezroq)
python main.py --parallel --workers 3 --query "python tutorial"
```

Natijalar: `output/` papkasida
- `output.json` — barcha video ma'lumotlari
- `output.csv`  — CSV format
- `analytics.json` — statistika
- `report.html` — vizual hisobot

## 3. FastAPI Dashboard

```bash
python server.py
# Brauzerda oching: http://localhost:8000
```

## 4. Docker

```bash
docker build -t yt-automation .
docker run --rm -v $(pwd)/output:/app/output yt-automation
```
