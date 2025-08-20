FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY README.md ./

RUN pip install --upgrade pip && \
    pip install uv hatchling

COPY src ./src
COPY docs ./docs
COPY scripts ./scripts

RUN uv sync

ENV TZ=Asia/Shanghai
EXPOSE 8000

CMD ["uv", "run", "--no-sync", "python", "-m", "mcp_12306.server"]
