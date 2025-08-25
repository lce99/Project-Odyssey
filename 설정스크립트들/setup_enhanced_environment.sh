#!/bin/bash
# setup_enhanced_environment.sh - Project Odysseus 고도화된 환경 원클릭 설정

set -e

# 색상 및 로깅 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${PURPLE}🔧 $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║            🚀 Project Odysseus Enhanced Setup            ║"
    echo "║         리버스 프록시 + 12-Factor App 통합 환경          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 전체 설정 프로세스
setup_enhanced_environment() {
    print_banner
    
    log_info "Project Odysseus 고도화된 환경을 설정합니다"
    echo
    
    # Step 1: 환경 검증
    log_step "1️⃣ 환경 검증 및 준비"
    check_prerequisites
    
    # Step 2: 설정 파일 마이그레이션
    log_step "2️⃣ 설정 파일 마이그레이션 (Pydantic 통합)"
    migrate_config_files
    
    # Step 3: 환경 변수 설정
    log_step "3️⃣ 12-Factor App 환경 변수 설정"
    setup_environment_variables
    
    # Step 4: 도메인 설정
    log_step "4️⃣ 리버스 프록시 도메인 설정"
    setup_local_domains
    
    # Step 5: Docker 네트워크 및 볼륨 준비
    log_step "5️⃣ Docker 인프라 준비"
    setup_docker_infrastructure
    
    # Step 6: 서비스 시작
    log_step "6️⃣ 통합 서비스 시작"
    start_enhanced_services
    
    # Step 7: 검증 및 테스트
    log_step "7️⃣ 환경 검증 및 테스트"
    verify_enhanced_environment
    
    # 완료 안내
    show_completion_guide
}

# 사전 요구사항 검증
check_prerequisites() {
    log_info "사전 요구사항 확인 중..."
    
    # Docker 및 Docker Compose 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되지 않았습니다"
        exit 1
    fi
    
    # Python 확인
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        log_error "Python이 설치되지 않았습니다"
        exit 1
    fi
    
    # 디스크 공간 확인 (최소 2GB 필요)
    available_space=$(df . | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 2097152 ]; then  # 2GB in KB
        log_warning "디스크 공간이 부족할 수 있습니다 (권장: 2GB 이상)"
    fi
    
    log_success "사전 요구사항 확인 완료"
}

# 설정 파일 마이그레이션
migrate_config_files() {
    log_info "Pydantic 통합 설정으로 마이그레이션 중..."
    
    # 기존 config.py 백업
    if [ -f config.py ]; then
        cp config.py "config_backup_$(date +%Y%m%d_%H%M%S).py"
        log_info "기존 config.py 백업 완료"
    fi
    
    # 새로운 통합 설정 적용
    if [ -f config_refactored.py ]; then
        cp config_refactored.py config.py
        log_success "Pydantic 통합 설정 적용 완료"
    else
        log_error "config_refactored.py 파일을 찾을 수 없습니다"
        exit 1
    fi
    
    # 설정 검증
    if python -c "import config; print('Config import successful')"; then
        log_success "새로운 설정 파일 검증 완료"
    else
        log_error "새로운 설정 파일에 오류가 있습니다"
        exit 1
    fi
}

# 환경 변수 설정
setup_environment_variables() {
    log_info "12-Factor App 환경 변수 설정 중..."
    
    # .env 파일 생성
    if [ ! -f .env ]; then
        if [ -f .env.12factor ]; then
            cp .env.12factor .env
            log_info "12-Factor App .env 파일 생성 완료"
        else
            log_error ".env.12factor 템플릿을 찾을 수 없습니다"
            exit 1
        fi
    else
        log_warning ".env 파일이 이미 존재합니다"
        read -p "12-Factor App 버전으로 교체하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env .env.backup
            cp .env.12factor .env
            log_info "환경 변수 파일 업데이트 완료"
        fi
    fi
    
    # 필수 환경 변수 체크
    log_info "필수 환경 변수 확인 중..."
    source .env
    
    required_vars=(
        "DB__PASSWORD"
        "EXCHANGES__BINANCE_API_KEY"
        "MONITORING__TELEGRAM__BOT_TOKEN"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [[ "${!var}" == *"your_"* ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_warning "다음 환경 변수들을 설정해야 합니다:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo
        log_info ".env 파일을 편집하여 실제 값들을 입력하세요"
        read -p "지금 편집하시겠습니까? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        log_success "모든 필수 환경 변수 설정됨"
    fi
}

# 로컬 도메인 설정
setup_local_domains() {
    log_info "리버스 프록시 도메인 설정 중..."
    
    if [ -f setup_domains.sh ]; then
        chmod +x setup_domains.sh
        ./setup_domains.sh setup
    else
        log_warning "setup_domains.sh를 찾을 수 없음 - 수동 설정 필요"
        echo "다음 도메인들을 /etc/hosts에 추가하세요:"
        echo "127.0.0.1    odysseus.local"
        echo "127.0.0.1    grafana.odysseus.local"
        echo "127.0.0.1    jupyter.odysseus.local"
        echo "127.0.0.1    prometheus.odysseus.local"
        echo "127.0.0.1    adminer.odysseus.local"
    fi
}

# Docker 인프라 준비
setup_docker_infrastructure() {
    log_info "Docker 인프라 준비 중..."
    
    # 필요한 디렉토리 생성
    mkdir -p nginx/conf.d logs data ml_models results backups
    mkdir -p monitoring/{grafana,prometheus,vector}
    mkdir -p scripts/{db,backup}
    
    # Nginx 설정 디렉토리 확인
    if [ ! -f nginx/nginx.conf ]; then
        log_warning "nginx/nginx.conf 파일이 없습니다 - 기본 설정 생성 중..."
        # 간단한 기본 설정 생성
        cat > nginx/nginx.conf << 'EOF'
events { worker_connections 1024; }
http {
    upstream trading_bot { server trading-bot:8000; }
    server {
        listen 80;
        server_name odysseus.local;
        location / { proxy_pass http://trading_bot; }
    }
}
EOF
    fi
    
    # Docker 네트워크 및 볼륨 생성
    docker network create odysseus-frontend 2>/dev/null || true
    docker network create odysseus-backend 2>/dev/null || true
    docker network create odysseus-database 2>/dev/null || true
    
    log_success "Docker 인프라 준비 완료"
}

# 서비스 시작
start_enhanced_services() {
    log_info "통합 서비스 시작 중..."
    
    # 사용자에게 시작 모드 선택
    echo "시작할 환경을 선택하세요:"
    echo "1) 기본 환경 (DB + Bot + Nginx)"
    echo "2) 개발 환경 (+ 개발 도구들)"
    echo "3) 전체 환경 (+ 모니터링 + 분석 도구)"
    
    read -p "선택 (1-3): " mode_choice
    
    case $mode_choice in
        1)
            log_info "기본 환경 시작 중..."
            docker-compose -f docker-compose-enhanced.yml up -d nginx timescaledb redis trading-bot
            ;;
        2)
            log_info "개발 환경 시작 중..."
            docker-compose -f docker-compose-enhanced.yml --profile dev --profile tools up -d
            ;;
        3)
            log_info "전체 환경 시작 중..."
            docker-compose -f docker-compose-enhanced.yml --profile dev --profile monitoring --profile tools --profile analysis up -d
            ;;
        *)
            log_error "잘못된 선택입니다"
            exit 1
            ;;
    esac
    
    # 서비스 시작 대기
    log_info "서비스 시작 대기 중... (최대 2분)"
    sleep 30
    
    # 컨테이너 상태 확인
    if docker-compose -f docker-compose-enhanced.yml ps | grep -q "Up"; then
        log_success "서비스 시작 완료"
    else
        log_error "일부 서비스 시작 실패"
        docker-compose -f docker-compose-enhanced.yml ps
        exit 1
    fi
}

# 환경 검증
verify_enhanced_environment() {
    log_info "고도화된 환경 검증 중..."
    
    # 도메인 접속 테스트
    test_urls=(
        "http://odysseus.local/health"
        "http://status.odysseus.local"
    )
    
    for url in "${test_urls[@]}"; do
        if curl -f -s "$url" > /dev/null; then
            echo "✅ $url - 접속 성공"
        else
            echo "❌ $url - 접속 실패"
        fi
    done
    
    # 컨테이너 헬스체크
    log_info "컨테이너 헬스체크..."
    healthy_services=0
    total_services=0
    
    for service in nginx timescaledb redis trading-bot; do
        total_services=$((total_services + 1))
        if docker-compose -f docker-compose-enhanced.yml ps "$service" | grep -q "healthy\|Up"; then
            echo "✅ $service - 정상"
            healthy_services=$((healthy_services + 1))
        else
            echo "❌ $service - 비정상"
        fi
    done
    
    if [ "$healthy_services" -eq "$total_services" ]; then
        log_success "모든 핵심 서비스 정상 작동"
    else
        log_warning "$healthy_services/$total_services 서비스만 정상 작동"
    fi
    
    # 데이터베이스 연결 테스트
    log_info "데이터베이스 연결 테스트..."
    if docker-compose -f docker-compose-enhanced.yml exec -T timescaledb pg_isready -U postgres; then
        log_success "TimescaleDB 연결 정상"
    else
        log_error "TimescaleDB 연결 실패"
    fi
    
    # Redis 연결 테스트
    log_info "Redis 연결 테스트..."
    if docker-compose -f docker-compose-enhanced.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis 연결 정상"
    else
        log_error "Redis 연결 실패"
    fi
}

# 완료 가이드 출력
show_completion_guide() {
    echo
    log_success "🎉 Project Odysseus 고도화된 환경 설정 완료!"
    
    echo
    echo -e "${GREEN}🌐 리버스 프록시 기반 접속 URL:${NC}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│ 🚀 메인 대시보드: http://odysseus.local                 │"
    echo "│ 📊 Grafana: http://grafana.odysseus.local               │"
    echo "│ 📓 Jupyter: http://jupyter.odysseus.local               │"
    echo "│ 🔍 Prometheus: http://prometheus.odysseus.local         │"
    echo "│ 🗃️ Adminer: http://adminer.odysseus.local               │"
    echo "│ 🔴 Redis: http://redis.odysseus.local                   │"
    echo "│ 🛠️ 개발환경: http://dev.odysseus.local                  │"
    echo "│ 📧 MailHog: http://mailhog.odysseus.local (개발용)       │"
    echo "│ 📊 Nginx 상태: http://status.odysseus.local             │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo
    
    echo -e "${BLUE}🔧 관리 명령어:${NC}"
    echo "📊 상태 확인:"
    echo "  docker-compose -f docker-compose-enhanced.yml ps"
    echo "  curl http://odysseus.local/health"
    echo
    echo "📝 로그 확인:"
    echo "  docker-compose -f docker-compose-enhanced.yml logs -f trading-bot"
    echo "  docker-compose -f docker-compose-enhanced.yml logs -f nginx"
    echo
    echo "🔄 서비스 관리:"
    echo "  docker-compose -f docker-compose-enhanced.yml restart"
    echo "  docker-compose -f docker-compose-enhanced.yml down"
    echo
    echo "🔍 디버깅:"
    echo "  docker-compose -f docker-compose-enhanced.yml exec trading-bot bash"
    echo "  docker-compose -f docker-compose-enhanced.yml exec nginx nginx -t"
    echo
    
    echo -e "${YELLOW}⚠️ 중요한 다음 단계:${NC}"
    echo "1. .env 파일에서 실제 API 키들을 설정하세요"
    echo "2. http://odysseus.local 접속하여 대시보드 확인"
    echo "3. Grafana(grafana.odysseus.local)에서 모니터링 설정"
    echo "4. 첫 번째 모듈 개발 시작"
    echo
    
    echo -e "${GREEN}💡 개발 팁:${NC}"
    echo "🔄 실시간 개발: 코드 변경시 자동 반영됩니다"
    echo "📊 모니터링: Grafana에서 실시간 메트릭 확인"
    echo "🐞 디버깅: http://dev.odysseus.local에서 개발 도구 사용"
    echo "📓 분석: Jupyter Lab에서 데이터 분석 및 백테스팅"
}

# 개별 기능들
migrate_config_files() {
    if [ ! -f config_refactored.py ]; then
        log_error "config_refactored.py가 없습니다. 먼저 생성해야 합니다."
        return 1
    fi
    
    # 백업 및 적용
    [ -f config.py ] && cp config.py "config_backup_$(date +%Y%m%d_%H%M%S).py"
    cp config_refactored.py config.py
    
    # 문법 검증
    if python -m py_compile config.py; then
        log_success "새로운 통합 설정 적용 완료"
    else
        log_error "설정 파일에 문법 오류가 있습니다"
        return 1
    fi
}

setup_environment_variables() {
    if [ ! -f .env ]; then
        if [ -f .env.12factor ]; then
            cp .env.12factor .env
            log_success "12-Factor App 환경 변수 파일 생성"
        else
            log_error ".env.12factor 템플릿이 없습니다"
            return 1
        fi
    fi
    
    # 환경 변수 검증
    python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['DB__PASSWORD', 'EXCHANGES__BINANCE_API_KEY']
missing = [var for var in required if not os.getenv(var) or os.getenv(var).startswith('your_')]

if missing:
    print(f'⚠️ 설정 필요: {missing}')
    print('nano .env  # 편집하여 실제 값 입력')
else:
    print('✅ 환경 변수 검증 완료')
"
}

setup_local_domains() {
    if [ -f setup_domains.sh ]; then
        chmod +x setup_domains.sh
        ./setup_domains.sh setup
    else
        log_warning "setup_domains.sh가 없습니다 - 수동 설정 필요"
    fi
}

setup_docker_infrastructure() {
    # 필요한 디렉토리들 생성
    mkdir -p {nginx/conf.d,logs,data,ml_models,results,backups}
    mkdir -p monitoring/{grafana,prometheus}
    mkdir -p scripts/db
    
    # Docker 네트워크 생성
    docker network create odysseus-frontend 2>/dev/null || true
    docker network create odysseus-backend 2>/dev/null || true
    docker network create odysseus-database 2>/dev/null || true
    
    log_success "Docker 인프라 준비 완료"
}

# 선택적 기능들
setup_ssl_certificates() {
    log_info "개발용 SSL 인증서 생성 중..."
    
    mkdir -p nginx/certs
    
    # 자체 서명 인증서 생성
    if [ ! -f nginx/certs/odysseus.crt ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/certs/odysseus.key \
            -out nginx/certs/odysseus.crt \
            -subj "/C=KR/ST=Seoul/L=Seoul/O=Odysseus/CN=*.odysseus.local"
        
        log_success "SSL 인증서 생성 완료"
    fi
}

setup_monitoring_configs() {
    log_info "모니터링 설정 파일 생성 중..."
    
    # Prometheus 설정
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-bot'
    static_configs:
      - targets: ['trading-bot:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']
    metrics_path: '/nginx_status'
EOF
    
    log_success "모니터링 설정 생성 완료"
}

# 유틸리티 명령어들
show_status() {
    echo "📊 현재 서비스 상태:"
    docker-compose -f docker-compose-enhanced.yml ps
    echo
    echo "🌐 네트워크 상태:"
    docker network ls | grep odysseus
    echo
    echo "📦 볼륨 상태:"
    docker volume ls | grep odysseus
}

show_logs() {
    local service=${1:-""}
    if [ -z "$service" ]; then
        docker-compose -f docker-compose-enhanced.yml logs -f
    else
        docker-compose -f docker-compose-enhanced.yml logs -f "$service"
    fi
}

# 메인 실행부
main() {
    local command=${1:-"setup"}
    
    case "$command" in
        "setup")
            setup_enhanced_environment
            ;;
        "migrate-config")
            migrate_config_files
            ;;
        "setup-domains")
            setup_local_domains
            ;;
        "start")
            start_enhanced_services
            ;;
        "verify")
            verify_enhanced_environment
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "${2:-}"
            ;;
        "ssl")
            setup_ssl_certificates
            ;;
        "monitoring")
            setup_monitoring_configs
            ;;
        "help"|"-h"|"--help")
            echo "Project Odysseus Enhanced Setup"
            echo "사용법: $0 <command>"
            echo
            echo "Commands:"
            echo "  setup           - 전체 환경 설정 (기본)"
            echo "  migrate-config  - Pydantic 설정으로 마이그레이션"
            echo "  setup-domains   - 로컬 도메인 설정"
            echo "  start           - 서비스 시작"
            echo "  verify          - 환경 검증"
            echo "  status          - 현재 상태 확인"
            echo "  logs [service]  - 로그 확인"
            echo "  ssl             - SSL 인증서 생성"
            echo "  monitoring      - 모니터링 설정 생성"
            ;;
        *)
            log_error "알 수 없는 명령어: $command"
            echo "사용법: $0 help"
            exit 1
            ;;
    esac
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi