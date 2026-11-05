FROM python:3.13-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY reaper reaper
RUN uv pip install --system --no-cache .
COPY --chmod=555 ./bin/keelson-storage-reaper.py /usr/local/bin/keelson-storage-reaper
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/bin/bash", "-c"]
