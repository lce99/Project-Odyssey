# 📦 Project Odysseus 의존성 관리 가이드

## 🏗️ 패키지 구조

```
requirements/
├── requirements.txt           # 🚀 운영 환경 (필수)
├── requirements-dev.txt       # 🧪 개발 환경
├── requirements-minimal.txt   # 🎯 최소 환경 (미래)
└── requirements-optional.txt  # ✨ 선택 기능 (미래)
```

## 📋 핵심 패키지 분류

### Tier 1: 절대 필수 (Cannot Remove)
```txt
pandas>=2.0.0          # 데이터 처리의 핵심
numpy>=1.24.0          # 수치 계산 기반
ccxt>=4.2.0            # 거래소 연동 필수
psycopg2-binary>=2.9.7 # TimescaleDB 연결
python-dotenv>=1.0.0   # 환경 변수 관리
loguru>=0.7.2          # 로깅 시스템
```

### Tier 2: 핵심 기능 (Core Features)
```txt
statsmodels>=0.14.0    # 통계 분석 (공적분 검정)
scipy>=1.10.0          # 과학 계산
scikit-learn>=1.3.0    # 머신러닝 기반
xgboost>=2.0.0         # ML 모델
pykalman>=0.9.5        # 칼만 필터
arch>=6.2.0            # GARCH 모델
```

### Tier 3: 운영 지원 (Operations)
```txt
apscheduler>=3.4.0     # 작업 스케줄링
fastapi>=0.103.0       # API 서버
requests>=2.31.0       # HTTP 클라이언트
aiohttp>=3.8.5         # 비동기 HTTP
websockets>=11.0.3     # WebSocket
python-telegram-bot>=20.5  # 알림
```

### Tier 4: 최적화 (Optional)
```txt
ta>=0.10.2             # 기술적 분석
yfinance>=0.2.20       # 추가 데이터
plotly>=5.17.0         # 시각화
numba>=0.58.0          # 성능 향상
```

## 🔧 설치 시나리오

### 1. 🚀 프로덕션 최적화 설치
```bash
# 최소한의 패키지로 운영
pip install pandas numpy ccxt psycopg2-binary python-dotenv loguru \
           statsmodels scipy scikit-learn xgboost pykalman arch \
           apscheduler requests python-telegram-bot

# 크기: ~200MB (기본 대비 60% 절약)
```

### 2. 🧪 개발 환경 풀 설치
```bash
pip install -r requirements-dev.txt
# 크기: ~500MB (모든 도구 포함)
```

### 3. 💻 로컬 테스트 설치
```bash
# 핵심 기능만 + 개발 도구
pip install -r requirements.txt pytest black flake8
# 크기: ~250MB
```

### 4. 🐳 Docker 경량화 설치
```bash
# multi-stage build에서 사용
pip install --no-cache-dir pandas numpy ccxt psycopg2-binary \
           python-dotenv loguru statsmodels xgboost
# 크기: ~150MB
```

## 📊 패키지 크기 분석

| 패키지 | 크기 | 역할 | 필수도 |
|--------|------|------|--------|
| pandas | ~45MB | 데이터 처리 | ⭐⭐⭐⭐⭐ |
| numpy | ~20MB | 수치 계산 | ⭐⭐⭐⭐⭐ |
| scipy | ~35MB | 과학 계산 | ⭐⭐⭐⭐ |
| scikit-learn | ~30MB | 머신러닝 | ⭐⭐⭐⭐ |
| xgboost | ~25MB | 부스팅 | ⭐⭐⭐ |
| statsmodels | ~15MB | 통계 분석 | ⭐⭐⭐⭐ |
| plotly | ~28MB | 시각화 | ⭐⭐ |
| jupyter | ~50MB | 개발 환경 | ⭐⭐ |

## 🚀 성능 최적화 팁

### 1. Import 최적화
```python
# ❌ 느림: 전체 모듈 import
import pandas as pd
import numpy as np
import sklearn

# ✅ 빠름: 필요한 것만 import
from pandas import DataFrame, Series
from numpy import array, mean
from sklearn.cluster import KMeans
```

### 2. 조건부 Import
```python
# 선택적 기능은 런타임에 import
def create_advanced_chart():
    try:
        import plotly.graph_objects as go
        # 차트 생성 로직
    except ImportError:
        logger.warning("Plotly not installed, using basic charts")
        return create_basic_chart()
```

### 3. Lazy Loading
```python
class AdvancedAnalytics:
    def __init__(self):
        self._ta_lib = None
    
    @property
    def ta_lib(self):
        if self._ta_lib is None:
            try:
                import talib
                self._ta_lib = talib
            except ImportError:
                self._ta_lib = False
        return self._ta_lib
```

## 🔍 패키지 버전 관리

### 1. 버전 고정 전략
```txt
# 🔒 완전 고정 (CI/CD)
pandas==2.1.3
numpy==1.25.2

# 🔄 마이너 업데이트 허용 (권장)
pandas~=2.1.0
numpy~=1.25.0

# ⬆️ 호환성 범위 (개발)
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
```

### 2. 보안 업데이트 체크
```bash
# 취약점 검사
safety check

# 업데이트 가능한 패키지 확인
pip list --outdated

# 특정 패키지 업데이트
pip install --upgrade pandas
```

### 3. 의존성 충돌 해결
```bash
# 의존성 트리 확인
pipdeptree

# 충돌 해결 도구
pip-tools compile requirements.in
pip-tools sync
```

## 🐳 Docker 최적화

### Multi-stage Dockerfile
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install --no-cache-dir pandas numpy ccxt
RUN pip freeze > /tmp/requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /tmp/requirements.txt .
# 크기: ~200MB (기본 대비 70% 절약)
```

### .dockerignore 최적화
```
# 불필요한 파일 제외
__pycache__/
*.pyc
.git/
.vscode/
tests/
docs/
*.md
requirements-dev.txt
```

## 🧪 대안 패키지 고려

### 경량화 대안
| 기본 패키지 | 경량 대안 | 크기 절약 | 주의사항 |
|-------------|-----------|-----------|----------|
| pandas | polars | ~70% | API 다름 |
| numpy | cupy | ~30% | GPU 필요 |
| requests | httpx | ~20% | 기능 유사 |
| plotly | matplotlib | ~60% | 기능 제한 |

### 성능 향상 대안
```python
# 고성능 수치 계산
import numba  # JIT 컴파일
import cupy   # GPU 가속 (NVIDIA)
import dask   # 병렬 처리

# 빠른 데이터 처리
import polars  # Rust 기반
import vaex    # Out-of-core 처리
```

## 📈 모니터링 및 프로파일링

### 1. Import 시간 측정
```python
import time
import sys

def timed_import(module_name):
    start = time.time()
    __import__(module_name)
    end = time.time()
    print(f"{module_name}: {end-start:.3f}s")

# 주요 모듈 import 시간 체크
timed_import('pandas')
timed_import('numpy')
timed_import('ccxt')
```

### 2. 메모리 사용량 모니터링
```python
import psutil
import sys

def check_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"메모리 사용량: {memory_mb:.1f}MB")

check_memory()  # import 전후 비교
```

### 3. 패키지 크기 분석
```bash
# 설치된 패키지 크기 확인
pip-autoremove --dry-run --list
du -sh venv/lib/python3.11/site-packages/*
```

## 🔄 정기 유지보수

### 월간 체크리스트
- [ ] 보안 업데이트 확인 (`safety check`)
- [ ] 사용하지 않는 패키지 제거
- [ ] 새로운 버전 호환성 테스트
- [ ] 의존성 트리 최적화

### 분기별 체크리스트
- [ ] 주요 패키지 버전 업데이트 검토
- [ ] 대안 패키지 성능 비교
- [ ] Docker 이미지 크기 최적화
- [ ] 벤치마크 테스트 실행

---
**💡 팁**: `pip-tools`를 사용하여 `requirements.in`에서 고수준 의존성을 관리하고, `requirements.txt`에서 정확한 버전을 고정하는 것이 좋습니다.