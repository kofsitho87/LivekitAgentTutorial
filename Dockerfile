# LiveKit Agent를 위한 최소한의 Docker 컨테이너 빌드 예제 (UV 사용)
# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Python이 pyc 파일을 생성하지 않도록 방지
ENV PYTHONDONTWRITEBYTECODE=1

# Python이 stdout과 stderr를 버퍼링하지 않도록 설정
# (애플리케이션이 버퍼링으로 인해 로그 없이 크래시되는 상황 방지)
ENV PYTHONUNBUFFERED=1

# UV 설치 (최신 버전)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# gcc, g++ 및 기타 빌드 의존성 설치 (root 권한으로)
RUN apt-get update && \
    apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# pyproject.toml과 uv.lock 파일 복사 (있는 경우)
COPY pyproject.toml uv.lock* ./

# UV를 사용하여 의존성 설치 (root 권한으로 시스템에 설치)
RUN uv pip install --system -r pyproject.toml

# 또는 requirements.txt가 있는 경우:
# COPY requirements.txt .
# RUN uv pip install --system -r requirements.txt

# 앱이 실행될 비특권 사용자 생성
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# 사용자 전환
USER appuser

# 사용자 홈 디렉토리로 작업 디렉토리 변경
WORKDIR /home/appuser/app

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser . .

# LiveKit Agent 시작 명령
CMD ["python", "langgraph_agent.py", "start"]