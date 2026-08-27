FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 riskguard \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin riskguard \
    && mkdir -p /app/data \
    && chown -R riskguard:riskguard /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY scripts ./scripts
COPY reports/model/xgboost_baseline.json ./reports/model/xgboost_baseline.json
COPY reports/behavioral/behavioral_risk_assessments.csv ./reports/behavioral/behavioral_risk_assessments.csv

RUN chown -R riskguard:riskguard /app
USER riskguard

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
