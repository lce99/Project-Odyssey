# 🐳 Project Odysseus Docker 설정 가이드

## 📋 개요

Project Odysseus는 Docker를 통해 완전한 개발 및 운영 환경을 제공합니다. TimescaleDB, Redis, 트레이딩 봇, 모니터링 도구 등을 통합된 환경에서 실행할 수 있습니다.

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Project Odysseus                     │
├─────────────────────────────────────────────────────────┤
│  🚀 Trading Bot (Python)                               │
│  ├── FastAPI Dashboard (Port 8000)                     │
│  ├── WebSocket Connections                             │
│  └── ML Models & Analytics                             │
├─────────────────────────────────────────────────────────┤
│  🗄️ Data Layer                                          │
│  ├── TimescaleDB (Port 5432) - 시계열 데이터           │
│  └── Redis (Port 6379) - 캐싱 & 세션                   │
├─────────────────────────────────────────────────────────┤
│  📊 Monitoring & Tools                                  │
│  ├── Grafana (Port 3000) - 대시보드                    │
│  ├── Prometheus (Port 9090) - 메트릭                   │
│  ├── Adminer (Port 8080) - DB 관리                     │
│  └── Jupyter Lab (Port 8888) - 데이터 분석             │
└─────────────────────────────────────────────────────────┘
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd project-odysseus

# 환경 변수 설정
cp .env.example .env
nano .env  # 실제 API 키 등을 설정

# Docker 스크립트 실행 권한 부여
chmod +x docker-scripts.sh
```

### 2. 기본 환경 시작
```bash
# 기본 서비스 시작 (DB + Trading Bot)
./docker-scripts.sh start

# 또는 docker-compose 직접 사용
docker-compose up -d
```

### 3. 개발 환경 시작
```bash
# 개발용 도구 포함
./docker-scripts.sh start-dev

# 또는
docker-compose --profile dev up -d
```

### 4. 전체 환경 시작 (모니터링 포함)
```bash
# 모든 서비스 포함
./docker-scripts.sh start-full

# 또는
docker-compose --profile dev --profile monitoring --profile tools up -d
```

## 📦 Docker 구성 요소

### 🎯 Core Services (기본)

#### 1. **timescaledb** - 시계열 데이터베이스
- **이미지**: `timescale/timescaledb:2.14.2-pg15`
- **포트**: 5432
- **용량**: ~500MB
- **역할**: 가격 데이터, 거래 기록, 분석 결과 저장

```bash
# 직접 접속
docker-compose exec timescaledb psql -U postgres odysseus_trading

# 백업
./docker-scripts.sh db-backup production
```

#### 2. **redis** - 메모리 캐시
- **이미지**: `redis:7-alpine`
- **포트**: 6379
- **용량**: ~50MB
- **역할**: 세션 관리, 실시간 데이터 캐싱

#### 3. **trading-bot** - 메인 애플리케이션
- **이미지**: `odysseus:latest` (자체 빌드)
- **포트**: 8000 (Dashboard)
- **용량**: ~800MB
- **역할**: 페어 트레이딩 로직, API 서버

### 🛠️ Development Services (개발용)

#### 4. **dev-environment** - 개발 환경
- **이미지**: `odysseus:dev`
- **포트**: 8001 (Dashboard), 8888 (Jupyter), 5678 (Debugger)
- **기능**: 실시간 코드 반영, 디버깅 도구

#### 5. **notebook** - 데이터 분석
- **이미지**: `odysseus:notebook`  
- **포트**: 8889
- **기능**: Jupyter Lab, 고급 데이터 분석 도구

### 📊 Monitoring Services (모니터링)

#### 6. **grafana** - 대시보드
- **이미지**: `grafana/grafana:10.2.0`
- **포트**: 3000
- **계정**: admin / odysseus123

#### 7. **prometheus** - 메트릭 수집
- **이미지**: `prom/prometheus:v2.47.0`
- **포트**: 9090

### 🔧 Utility Services (도구)

#### 8. **adminer** - DB 관리 도구
- **포트**: 8080
- **기능**: TimescaleDB 웹 관리

#### 9. **redis-commander** - Redis 관리
- **포트**: 8081

#### 10. **mailhog** - 이메일 테스트 (개발용)
- **포트**: 8025 (UI), 1025 (SMTP)

## 🎛️ Docker 스크립트 사용법

`docker-scripts.sh`는 프로젝트 관리를 위한 통합 스크립트입니다.

### 빌드 명령어
```bash
./docker-scripts.sh build-prod      # 운영용 이미지 빌드
./docker-scripts.sh build-dev       # 개발용 이미지 빌드  
./docker-scripts.sh build-all       # 모든 이미지 빌드
./docker-scripts.sh rebuild         # 캐시 없이 재빌드
```

### 실행 명령어
```bash
./docker-scripts.sh start           # 기본 서비스 시작
./docker-scripts.sh start-dev       # 개발 환경 시작
./docker-scripts.sh start-full      # 전체 서비스 시작
./docker-scripts.sh stop            # 모든 서비스 중지
./docker-scripts.sh restart         # 서비스 재시작
```

### 모니터링 명령어
```bash
./docker-scripts.sh logs trading-bot    # 특정 서비스 로그
./docker-scripts.sh status              # 서비스 상태 확인
./docker-scripts.sh health              # 헬스체크 실행
./docker-scripts.sh stats               # 리소스 사용량
```

### 데이터베이스 명령어
```bash
./docker-scripts.sh db-init             # DB 초기화
./docker-scripts.sh db-backup prod       # DB 백업
./docker-scripts.sh db-restore backup.sql # DB 복원
./docker-scripts.sh db-shell             # DB 쉘 접속
```

### 유틸리티 명령어
```bash
./docker-scripts.sh shell trading-bot   # 컨테이너 쉘 접속
./docker-scripts.sh clean               # 불필요한 리소스 정리
./docker-scripts.sh update              # 이미지 업데이트
```

## 🔧 환경별 설정

### 개발 환경 (Development)
```bash
# 개발 환경 시작
./docker-scripts.sh start-dev

# 특징:
# - 실시간 코드 반영
# - 디버깅 도구 활성화
# - Jupyter Lab 포함
# - 상세한 로깅
# - 개발용 데이터베이스 설정
```

### 운영 환경 (Production)
```bash
# 운영 환경 시작
./docker-scripts.sh start

# 특징:
# - 최적화된 이미지 사용
# - 보안 강화 설정
# - 리소스 제한 적용
# - 자동 재시작 정책
# - 운영 수준 로깅
```

### 테스트 환경 (Testing)
```bash
# 테스트용 환경 변수 설정
export TRADING_MODE=testnet
export DRY_RUN=true

# 테스트 환경 시작
docker-compose up -d
```

## 📊 서비스 접속 정보

| 서비스 | URL | 계정 | 설명 |
|--------|-----|------|------|
| Trading Dashboard | http://localhost:8000 | - | 메인 대시보드 |
| Dev Dashboard | http://localhost:8001 | - | 개발용 대시보드 |
| Jupyter Lab | http://localhost:8888 | - | 데이터 분석 |
| Grafana | http://localhost:3000 | admin/odysseus123 | 모니터링 |
| Prometheus | http://localhost:9090 | - | 메트릭 수집 |
| Adminer | http://localhost:8080 | postgres | DB 관리 |
| Redis Commander | http://localhost:8081 | - | Redis 관리 |
| MailHog | http://localhost:8025 | - | 이메일 테스트 |

## 🗄️ 데이터 관리

### 볼륨 구조
```
volumes/
├── timescaledb-data/     # PostgreSQL 데이터
├── redis-data/           # Redis 데이터
├── app-logs/            # 애플리케이션 로그
├── backtest-data/       # 백테스트 결과
└── ml-models/           # ML 모델 저장소
```

### 백업 전략
```bash
# 자동 백업 (매일 새벽 2시)
docker-compose --profile backup up -d backup

# 수동 백업
./docker-scripts.sh db-backup $(date +%Y%m%d)

# 설정 파일 백업
./docker-scripts.sh backup-config
```

### 데이터 복원
```bash
# 특정 백업에서 복원
./docker-scripts.sh db-restore backups/backup_20240101.sql

# 전체 환경 초기화
./docker-scripts.sh reset
```

## 🔍 디버깅 및 트러블슈팅

### 일반적인 문제들

#### 1. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tlnp | grep :5432
lsof -i :5432

# docker-compose.yml에서 포트 변경
ports:
  - "15432:5432"  # 외부 포트를 15432로 변경
```

#### 2. 볼륨 권한 문제
```bash
# 볼륨 권한 수정
sudo chown -R $USER:$USER ./data
sudo chmod -R 755 ./data
```

#### 3. 메모리 부족
```bash
# Docker 메모리 사용량 확인
docker stats

# 메모리 제한 설정
services:
  trading-bot:
    mem_limit: 1g
    memswap_limit: 1g
```

#### 4. 데이터베이스 연결 실패
```bash
# 네트워크 확인
docker-compose exec trading-bot ping timescaledb

# 로그 확인
docker-compose logs timescaledb
```

### 로그 분석
```bash
# 실시간 로그 모니터링
./docker-scripts.sh logs

# 특정 서비스 로그
docker-compose logs -f --tail=100 trading-bot

# 로그 파일 위치
./logs/trading-bot.log
./logs/error.log
```

### 성능 모니터링
```bash
# 리소스 사용량 실시간 확인
./docker-scripts.sh stats

# 개별 컨테이너 성능
docker exec -it odysseus-trading-bot top
```

## 🚀 배포 가이드

### 운영 환경 배포
```bash
# 1. 운영 환경 변수 설정
cp .env.example .env.production
nano .env.production  # 운영 설정 입력

# 2. 운영용 이미지 빌드
docker build -t odysseus:prod --target runtime .

# 3. 운영 환경 시작
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 자동 배포 (CI/CD)
```yaml
# .github/workflows/deploy.yml 예시
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and Deploy
        run: |
          ./docker-scripts.sh build-prod
          ./docker-scripts.sh stop
          ./docker-scripts.sh start
```

## 🔧 고급 설정

### 리소스 제한
```yaml
services:
  trading-bot:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 환경별 오버라이드
```bash
# 개발 환경
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 운영 환경  
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 테스트 환경
docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
```

### 스케일링
```bash
# 트레이딩 봇 인스턴스 확장
docker-compose up -d --scale trading-bot=3

# 로드 밸런서 추가
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## 📚 추가 리소스

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- [TimescaleDB 문서](https://docs.timescale.com/)
- [Redis 문서](https://redis.io/documentation)

## 🆘 도움이 필요한 경우

1. **로그 확인**: `./docker-scripts.sh logs`
2. **상태 점검**: `./docker-scripts.sh health`  
3. **환경 초기화**: `./docker-scripts.sh reset`
4. **GitHub Issues** 등록