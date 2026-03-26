FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN playwright install --with-deps chromium

RUN mkdir -p /app/output

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "localhost", "--port", "8000"]