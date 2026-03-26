# 🚀 YouTube Automation & Analytics Platform

A full-stack backend system that automates YouTube data extraction, performs analytics, and delivers real-time insights via API, WebSocket, and HTML dashboards.

---

## 📌 Overview

This project is a **YouTube scraping + analytics pipeline** built with modern Python tools.

It:

* Searches YouTube videos by query
* Extracts video metadata and top comments
* Performs analytics (views, likes, durations, trends)
* Stores data in JSON, CSV, and PostgreSQL
* Provides real-time progress updates via WebSockets
* Generates an interactive HTML report

---

## ⚙️ Core Features

* 🔍 YouTube search automation (Playwright)
* 🎬 Video metadata extraction
* 💬 Comment scraping (lazy-load handling)
* 📊 Analytics engine (views, likes, duration, channels)
* 📡 Real-time updates (WebSocket)
* 🗄️ PostgreSQL integration
* 📁 JSON & CSV export
* 📈 HTML dashboard with Chart.js
* 🐳 Fully Dockerized environment

---

## 🧠 Architecture

```
Client → FastAPI → JobManager → Scraper → Analyzer → Storage → Report
                             ↓
                        WebSocket (real-time updates)
```

### Layers:

* **API Layer** → FastAPI (`app.py`)
* **Orchestration** → JobManager
* **Scraping Layer** → Playwright (browser automation)
* **Parsing Layer** → Video + Comment parsers
* **Analytics Layer** → Analyzer
* **Storage Layer** → JSON / CSV / PostgreSQL
* **Realtime Layer** → WebSocket Manager
* **Presentation Layer** → HTML report

---

## 🛠️ Tech Stack

### Backend

* **Python 3.11**
* **FastAPI** — REST API & WebSocket server
* **Uvicorn** — ASGI server

### Scraping

* **Playwright** — browser automation (YouTube scraping)

### Data & Processing

* **Dataclasses** — structured data models
* **AsyncIO** — concurrency & performance

### Database

* **PostgreSQL** — persistent storage
* **SQLAlchemy (async)** — ORM

### Analytics

* Custom analytics engine (views, likes, duration, etc.)

### Visualization

* **Chart.js** — HTML dashboard charts

### DevOps

* **Docker** — containerization
* **Docker Compose** — multi-service orchestration

---

## 📂 Project Structure

```
api/
  app.py
  job_manager.py
  ws_manager.py

scraper/
  browser.py
  search.py
  video_parser.py
  comment_parser.py

analytics/
  analyzer.py

models/
  video.py

utils/
  storage.py
  reporter.py
  database.py

config.py
main.py
Dockerfile
docker-compose.yml
```

---

## 🚀 How to Run

## 🔹 Option 1 — Docker (Recommended)

### Requirements:

* Docker
* Docker Compose

### Run:

```bash
docker compose up --build
```

Open:

```
http://localhost:8000
```

---

## 🔹 Option 2 — Local Development

### Requirements:

* Python 3.11+
* PostgreSQL installed

### 1. Clone repo

```bash
git clone <your-repo-url>
cd youtube-automation
```

---

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Install Playwright browsers

```bash
playwright install chromium
```

---

### 5. Setup environment

Create `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/youtube_db
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:password@localhost:5432/youtube_db
```

---

### 6. Run server

```bash
uvicorn api.app:app --reload
```

---

## 🔹 Option 3 — CLI Mode

Run without API:

```bash
python main.py --query "python tutorial"
```

Options:

* `--max-videos`
* `--parallel`
* `--workers`
* `--format json/csv/both`

---

## 📡 API Usage

### Start scraping

```http
POST /api/scrape
```

Body:

```json
{
  "query": "django",
  "max_videos": 10
}
```

Response:

```json
{
  "job_id": "abcd1234",
  "ws_url": "/ws/abcd1234"
}
```

---

### WebSocket (real-time)

```
ws://localhost:8000/ws/{job_id}
```

---

### Get results

```
GET /api/jobs/{job_id}/results
```

---

### Get analytics

```
GET /api/jobs/{job_id}/analytics
```

---

### Get HTML report

```
GET /api/jobs/{job_id}/report
```

---

## 📊 Data Flow

1. User sends query
2. JobManager creates job
3. Scraper collects video URLs
4. VideoParser extracts metadata
5. CommentParser extracts comments
6. Analyzer computes insights
7. Storage saves results
8. ReportGenerator builds HTML dashboard
9. WebSocket streams progress updates

---

## ⚠️ Limitations

* Relies on YouTube DOM (can break if UI changes)
* No distributed job queue (single-node)
* In-memory job tracking (non-persistent)
* Not optimized for massive scale (yet)

---

## 🚀 Future Improvements

* Redis + Celery queue
* Distributed scraping
* Frontend dashboard (React)
* AI-based comment sentiment analysis
* Caching layer
* Rate limiting & proxy rotation

---

## 🧠 Key Design Decisions

* Separation of concerns (scraping vs analytics vs storage)
* Async-first architecture
* Playwright over requests (handles dynamic content)
* JSONB for flexible analytics storage
* WebSocket for real-time UX

---

## 👨‍💻 Author

Built as a practical system for learning:

* scraping
* backend architecture
* async systems
* real-world data pipelines

---

## 📄 License

MIT License
