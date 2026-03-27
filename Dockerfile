FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DISPLAY=:99

# Tizim paketlarini o'rnatish
USER root
RUN apt-get update && apt-get install -y \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Loyihani nusxalash
COPY . .

# Brauzer o'rnatilmagan bo'lsa o'rnatadi, bor bo'lsa tekshiradi
RUN playwright install chromium --with-deps

# 5. Papka va ruxsatnomalar
RUN mkdir -p /app/output && chmod +x /app/start.sh

RUN sed -i 's/\r$//' /app/start.sh

EXPOSE 8000

CMD ["/bin/bash", "/app/start.sh"]