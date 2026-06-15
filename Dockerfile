FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py daily_crawl_with_kakao.py kakao_config.example.json ./

CMD ["python", "daily_crawl_with_kakao.py"]
