FROM oven/bun:1.4.4 AS browser
WORKDIR /src
COPY frontend/web/package.json frontend/web/bun.lock ./frontend/web/
RUN cd frontend/web && bun install --frozen-lockfile
COPY frontend/web ./frontend/web
COPY data/circuits ./data/circuits
RUN cd frontend/web && bun --bun run build:public

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY brain ./brain
COPY world ./world
COPY simulation ./simulation
COPY experiments ./experiments
COPY frontend/*.py ./frontend/
COPY scripts/download_malecns.py ./scripts/download_malecns.py
COPY main.py gym_cli.py public_cli.py ./
COPY data/circuits ./data/circuits
COPY data/malecns ./data/malecns
COPY --from=browser /src/frontend/web/dist-public ./frontend/web/dist-public
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md ./
COPY licenses ./licenses
RUN groupadd --system gym && useradd --system --gid gym gym && mkdir -p data/raw data/runs && chown -R gym:gym data
USER gym
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s --start-period=300s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)"
ENTRYPOINT ["python", "-B", "main.py", "public-web"]
