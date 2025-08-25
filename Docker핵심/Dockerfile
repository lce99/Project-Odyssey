# Dockerfile - Project Odysseus 동적 적응형 페어 트레이딩 봇
# Multi-stage build for optimized production image

# =============================================================================
# Stage 1: System Dependencies Builder
# =============================================================================
FROM python:3.11-slim as system-builder

# 메타데이터 라벨
LABEL maintainer="Project Odysseus Team"
LABEL version="1.0.0"
LABEL description="Dynamic Adaptive Pairs Trading Bot"

# 빌드 인수 정의
ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHONUNBUFFERED=1
ARG PYTHONDONTWRITEBYTECODE=1

# 환경 변수 설정
ENV PYTHONUNBUFFERED=$PYTHONUNBUFFERED
ENV PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE
ENV PYTHONPATH=/app
ENV TZ=UTC

# 시스템 패키지 업데이트 및 필수 의존성 설치
RUN apt-get update && apt-get install -y \
    # 컴파일 도구들
    build-essential \
    gcc \
    g++ \
    make \
    # 라이브러리 개발 헤더들
    python3-dev \
    libpq-dev \
    libta-lib0-dev \
    # 시스템 유틸리티
    curl \
    wget \
    git \
    # 네트워킹
    ca-certificates \
    # 시간대 데이터
    tzdata \
    # 프로세스 관리
    supervisor \
    # 정리 도구
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# 시간대 설정
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# =============================================================================
# Stage 2: Python Dependencies Builder  
# =============================================================================
FROM system-builder as python-builder

# pip 업그레이드 및 빌드 도구 설치
RUN pip install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel \
    build

# 작업 디렉토리 설정
WORKDIR /build

# requirements 파일들 복사
COPY requirements.txt requirements-dev.txt ./

# Python 패키지 설치 (캐시 최적화)
# 큰 패키지부터 설치하여 레이어 캐싱 최적화
RUN pip install --no-cache-dir --user \
    # 큰 패키지들 먼저
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    scipy>=1.10.0 \
    scikit-learn>=1.3.0 \
    && pip install --no-cache-dir --user \
    # 나머지 패키지들
    -r requirements.txt

# TA-Lib 별도 설치 (실패해도 계속 진행)
RUN pip install --no-cache-dir --user TA-Lib || echo "TA-Lib installation failed, continuing..."

# 개발 환경인 경우 개발 도구 설치
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir --user -r requirements-dev.txt; \
    fi

# =============================================================================
# Stage 3: Runtime Image (Production)
# =============================================================================
FROM python:3.11-slim as runtime

# 빌드 인수 재정의
ARG PYTHONUNBUFFERED=1
ARG PYTHONDONTWRITEBYTECODE=1

# 환경 변수 설정
ENV PYTHONUNBUFFERED=$PYTHONUNBUFFERED
ENV PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE
ENV PYTHONPATH=/app
ENV TZ=UTC
ENV PATH="/home/appuser/.local/bin:$PATH"

# 런타임 의존성만 설치 (빌드 도구 제외)
RUN apt-get update && apt-get install -y \
    # PostgreSQL 클라이언트 라이브러리
    libpq5 \
    # TA-Lib 런타임 라이브러리
    libta-lib0 \
    # 시스템 유틸리티
    curl \
    ca-certificates \
    tzdata \
    # 프로세스 모니터링
    procps \
    # 네트워크 도구 (디버깅용)
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# 시간대 설정
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 보안을 위한 비특권 사용자 생성
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -d /home/appuser -s /bin/bash -c "App User" appuser && \
    mkdir -p /home/appuser/.local && \
    chown -R appuser:appgroup /home/appuser

# Python 패키지 복사 (builder stage에서)
COPY --from=python-builder --chown=appuser:appgroup \
    /root/.local /home/appuser/.local

# 앱 디렉토리 생성 및 권한 설정
RUN mkdir -p /app /app/logs /app/data /app/ml_models /app/results && \
    chown -R appuser:appgroup /app

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션 코드 복사
COPY --chown=appuser:appgroup . .

# 실행 권한 설정
RUN chmod +x scripts/*.sh 2>/dev/null || true

# 비특권 사용자로 전환
USER appuser

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 포트 노출
EXPOSE 8000

# 볼륨 설정
VOLUME ["/app/logs", "/app/data", "/app/ml_models"]

# 기본 명령어
CMD ["python", "main.py"]

# =============================================================================
# Stage 4: Development Image
# =============================================================================
FROM runtime as development

USER root

# 개발 도구 추가 설치
RUN apt-get update && apt-get install -y \
    # 개발 도구
    vim \
    nano \
    htop \
    git \
    # 네트워크 디버깅
    tcpdump \
    nmap \
    # 개발 편의 도구
    bash-completion \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 개발용 Python 패키지들 (이미 설치되어 있으면 스킵)
RUN pip install --no-cache-dir --user \
    ipython \
    jupyter \
    notebook \
    pytest \
    black \
    flake8 \
    mypy \
    || echo "Some development packages already installed"

# Jupyter 설정
RUN mkdir -p /home/appuser/.jupyter && \
    echo "c.NotebookApp.ip = '0.0.0.0'" > /home/appuser/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_root = True" >> /home/appuser/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /home/appuser/.jupyter/jupyter_notebook_config.py && \
    chown -R appuser:appgroup /home/appuser/.jupyter

# 개발용 추가 포트
EXPOSE 8888 5432

USER appuser

# 개발 모드 환경 변수
ENV DEVELOPMENT_MODE=true
ENV LOG_LEVEL=DEBUG

# 개발용 기본 명령어 (오버라이드 가능)
CMD ["bash", "-c", "echo 'Development environment ready!' && python main.py"]

# =============================================================================
# Build Instructions (빌드 가이드)
# =============================================================================

# 1. Production Build:
#    docker build -t odysseus:latest .
#    docker build -t odysseus:prod --target runtime .

# 2. Development Build:
#    docker build -t odysseus:dev --target development --build-arg INSTALL_DEV=true .

# 3. Lightweight Build (without TA-Lib):
#    docker build -t odysseus:minimal --build-arg SKIP_TALIB=true .

# 4. Multi-platform Build:
#    docker buildx build --platform linux/amd64,linux/arm64 -t odysseus:latest .

# =============================================================================
# Usage Examples (사용 예시)
# =============================================================================

# Run production container:
# docker run -d --name odysseus-bot \
#   --env-file .env \
#   -v $(pwd)/logs:/app/logs \
#   -v $(pwd)/data:/app/data \
#   odysseus:latest

# Run development container:  
# docker run -it --name odysseus-dev \
#   --env-file .env \
#   -v $(pwd):/app \
#   -p 8000:8000 -p 8888:8888 \
#   odysseus:dev bash

# Run with docker-compose:
# docker-compose up -d