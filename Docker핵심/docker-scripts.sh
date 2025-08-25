#!/bin/bash
# docker-scripts.sh - Project Odysseus Docker 관리 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 로고 및 제목
print_logo() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════╗"
    echo "║            🚀 Project Odysseus                ║"
    echo "║         Docker Management Scripts             ║"
    echo "╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 로그 함수들
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 도움말 출력
show_help() {
    print_logo
    echo "사용법: $0 <command> [options]"
    echo
    echo "📋 사용 가능한 명령어:"
    echo
    echo "🏗️  빌드 관련:"
    echo "  build-prod         - 운영용 이미지 빌드"
    echo "  build-dev          - 개발용 이미지 빌드"  
    echo "  build-all          - 모든 이미지 빌드"
    echo "  rebuild            - 캐시 없이 재빌드"
    echo
    echo "🚀 실행 관련:"
    echo "  start              - 기본 서비스 시작 (DB + Bot)"
    echo "  start-dev          - 개발 환경 시작"
    echo "  start-full         - 모든 서비스 시작 (모니터링 포함)"
    echo "  stop               - 모든 서비스 중지"
    echo "  restart            - 서비스 재시작"
    echo
    echo "📊 모니터링 관련:"
    echo "  logs [service]     - 로그 확인"
    echo "  status             - 서비스 상태 확인"
    echo "  health             - 헬스체크 실행"
    echo "  stats              - 리소스 사용량 확인"
    echo
    echo "🗄️  데이터베이스 관련:"
    echo "  db-init            - 데이터베이스 초기화"
    echo "  db-backup          - 데이터베이스 백업"
    echo "  db-restore [file]  - 데이터베이스 복원"
    echo "  db-shell           - 데이터베이스 쉘 접속"
    echo
    echo "🧹 정리 관련:"
    echo "  clean              - 사용하지 않는 컨테이너/이미지 정리"
    echo "  clean-all          - 모든 데이터 포함 정리 (주의!)"
    echo "  reset              - 전체 환경 초기화"
    echo
    echo "🔧 유틸리티:"
    echo "  shell [service]    - 서비스 쉘 접속"
    echo "  update             - 이미지 업데이트"
    echo "  backup-config      - 설정 파일 백업"
    echo
    echo "예시:"
    echo "  $0 start-dev                    # 개발 환경 시작"
    echo "  $0 logs trading-bot             # 트레이딩 봇 로그 확인"  
    echo "  $0 shell timescaledb            # DB 쉘 접속"
    echo "  $0 db-backup production         # 백업 생성"
}

# 환경 확인
check_environment() {
    log_info "환경 확인 중..."
    
    # Docker 설치 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다."
        exit 1
    fi
    
    # Docker Compose 설치 확인
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되지 않았습니다."
        exit 1
    fi
    
    # .env 파일 확인
    if [ ! -f .env ]; then
        log_warning ".env 파일이 없습니다."
        if [ -f .env.example ]; then
            log_info ".env.example에서 .env 파일을 생성합니다..."
            cp .env.example .env
            log_warning "⚠️  .env 파일을 편집하여 실제 값들을 설정해주세요!"
        fi
    fi
    
    log_success "환경 확인 완료"
}

# 이미지 빌드 함수들
build_prod() {
    log_info "운영용 이미지 빌드 중..."
    docker build -t odysseus:latest --target runtime .
    log_success "운영용 이미지 빌드 완료"
}

build_dev() {
    log_info "개발용 이미지 빌드 중..."
    docker build -t odysseus:dev --target development --build-arg INSTALL_DEV=true .
    log_success "개발용 이미지 빌드 완료"
}

build_all() {
    log_info "모든 이미지 빌드 중..."
    build_prod
    build_dev
    log_success "모든 이미지 빌드 완료"
}

rebuild() {
    log_info "캐시 없이 재빌드 중..."
    docker-compose build --no-cache
    log_success "재빌드 완료"
}

# 서비스 시작 함수들
start_basic() {
    log_info "기본 서비스 시작 중... (TimescaleDB + Trading Bot)"
    docker-compose up -d timescaledb redis trading-bot
    show_service_urls
    log_success "기본 서비스 시작 완료"
}

start_dev() {
    log_info "개발 환경 시작 중..."
    docker-compose --profile dev up -d
    show_service_urls
    log_success "개발 환경 시작 완료"
}

start_full() {
    log_info "전체 서비스 시작 중... (모니터링 + 도구 포함)"
    docker-compose --profile dev --profile monitoring --profile tools up -d
    show_service_urls
    log_success "전체 서비스 시작 완료"
}

# 서비스 URL 표시
show_service_urls() {
    echo
    echo -e "${GREEN}🌐 서비스 접속 정보:${NC}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│ 📊 Trading Bot Dashboard: http://localhost:8000        │"
    echo "│ 🛠️  Development Dashboard: http://localhost:8001       │"
    echo "│ 📓 Jupyter Lab: http://localhost:8888                  │"
    echo "│ 📈 Grafana: http://localhost:3000 (admin/odysseus123)  │"
    echo "│ 🔍 Prometheus: http://localhost:9090                   │"
    echo "│ 🗃️  Adminer: http://localhost:8080                     │"
    echo "│ 🔴 Redis Commander: http://localhost:8081              │"
    echo "│ 📧 MailHog: http://localhost:8025                      │"
    echo "│ 🌸 Flower: http://localhost:5555                       │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo
}

# 서비스 중지
stop_services() {
    log_info "모든 서비스 중지 중..."
    docker-compose down
    log_success "서비스 중지 완료"
}

# 서비스 재시작
restart_services() {
    log_info "서비스 재시작 중..."
    docker-compose restart
    log_success "서비스 재시작 완료"
}

# 로그 확인
show_logs() {
    local service=${1:-""}
    if [ -z "$service" ]; then
        log_info "모든 서비스 로그 출력 중..."
        docker-compose logs -f
    else
        log_info "$service 서비스 로그 출력 중..."
        docker-compose logs -f "$service"
    fi
}

# 서비스 상태 확인
check_status() {
    log_info "서비스 상태 확인 중..."
    echo
    docker-compose ps
    echo
    log_info "컨테이너 리소스 사용량:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 헬스체크 실행
health_check() {
    log_info "헬스체크 실행 중..."
    
    services=("timescaledb" "redis" "trading-bot")
    
    for service in "${services[@]}"; do
        echo -n "🔍 $service: "
        if docker-compose exec -T "$service" sh -c 'exit 0' 2>/dev/null; then
            echo -e "${GREEN}✅ Healthy${NC}"
        else
            echo -e "${RED}❌ Unhealthy${NC}"
        fi
    done
    
    echo
    log_info "상세 헬스체크 정보:"
    docker-compose ps
}

# 리소스 사용량 확인
show_stats() {
    log_info "실시간 리소스 사용량 모니터링 중... (Ctrl+C로 종료)"
    docker stats
}

# 데이터베이스 관련 함수들
db_init() {
    log_info "데이터베이스 초기화 중..."
    
    # TimescaleDB 컨테이너가 실행 중인지 확인
    if ! docker-compose ps timescaledb | grep -q "Up"; then
        log_info "TimescaleDB 시작 중..."
        docker-compose up -d timescaledb
        
        # DB가 완전히 시작될 때까지 대기
        log_info "데이터베이스 시작 대기 중..."
        for i in {1..30}; do
            if docker-compose exec -T timescaledb pg_isready -U postgres; then
                break
            fi
            echo -n "."
            sleep 2
        done
        echo
    fi
    
    log_success "데이터베이스 초기화 완료"
}

db_backup() {
    local backup_name=${1:-"backup_$(date +%Y%m%d_%H%M%S)"}
    log_info "데이터베이스 백업 생성 중... ($backup_name)"
    
    mkdir -p backups
    docker-compose exec -T timescaledb pg_dump -U postgres odysseus_trading > "backups/$backup_name.sql"
    
    log_success "백업 완료: backups/$backup_name.sql"
}

db_restore() {
    local backup_file=$1
    if [ -z "$backup_file" ]; then
        log_error "백업 파일을 지정해주세요."
        echo "사용법: $0 db-restore backups/backup_file.sql"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "백업 파일을 찾을 수 없습니다: $backup_file"
        exit 1
    fi
    
    log_warning "⚠️  데이터베이스를 복원하면 기존 데이터가 삭제됩니다!"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "데이터베이스 복원 중..."
        docker-compose exec -T timescaledb psql -U postgres -c "DROP DATABASE IF EXISTS odysseus_trading;"
        docker-compose exec -T timescaledb psql -U postgres -c "CREATE DATABASE odysseus_trading;"
        docker-compose exec -T timescaledb psql -U postgres odysseus_trading < "$backup_file"
        log_success "데이터베이스 복원 완료"
    else
        log_info "복원이 취소되었습니다."
    fi
}

db_shell() {
    log_info "데이터베이스 쉘 접속 중..."
    docker-compose exec timescaledb psql -U postgres odysseus_trading
}

# 정리 함수들
clean_docker() {
    log_info "사용하지 않는 Docker 리소스 정리 중..."
    docker system prune -f
    docker volume prune -f
    log_success "Docker 정리 완료"
}

clean_all() {
    log_error "⚠️  모든 데이터를 삭제합니다! (컨테이너, 이미지, 볼륨, 네트워크)"
    read -p "정말로 모든 데이터를 삭제하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "전체 환경 정리 중..."
        docker-compose down -v --rmi all
        docker system prune -af --volumes
        log_success "전체 정리 완료"
    else
        log_info "정리가 취소되었습니다."
    fi
}

reset_environment() {
    log_warning "전체 환경을 초기화합니다..."
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        clean_all
        build_all
        start_basic
        log_success "환경 초기화 완료"
    fi
}

# 유틸리티 함수들
service_shell() {
    local service=${1:-"trading-bot"}
    log_info "$service 쉘 접속 중..."
    docker-compose exec "$service" bash
}

update_images() {
    log_info "이미지 업데이트 중..."
    docker-compose pull
    log_success "이미지 업데이트 완료"
}

backup_config() {
    local backup_dir="config_backup_$(date +%Y%m%d_%H%M%S)"
    log_info "설정 파일 백업 중... ($backup_dir)"
    
    mkdir -p "$backup_dir"
    cp -r .env* config.py docker-compose*.yml Dockerfile* "$backup_dir/" 2>/dev/null || true
    
    log_success "설정 백업 완료: $backup_dir/"
}

# 메인 함수
main() {
    local command=$1
    shift
    
    case "$command" in
        # 빌드 관련
        "build-prod") check_environment && build_prod ;;
        "build-dev") check_environment && build_dev ;;
        "build-all") check_environment && build_all ;;
        "rebuild") check_environment && rebuild ;;
        
        # 실행 관련
        "start") check_environment && start_basic ;;
        "start-dev") check_environment && start_dev ;;
        "start-full") check_environment && start_full ;;
        "stop") stop_services ;;
        "restart") restart_services ;;
        
        # 모니터링 관련
        "logs") show_logs "$@" ;;
        "status") check_status ;;
        "health") health_check ;;
        "stats") show_stats ;;
        
        # 데이터베이스 관련
        "db-init") check_environment && db_init ;;
        "db-backup") check_environment && db_backup "$@" ;;
        "db-restore") check_environment && db_restore "$@" ;;
        "db-shell") check_environment && db_shell ;;
        
        # 정리 관련
        "clean") clean_docker ;;
        "clean-all") clean_all ;;
        "reset") reset_environment ;;
        
        # 유틸리티
        "shell") check_environment && service_shell "$@" ;;
        "update") update_images ;;
        "backup-config") backup_config ;;
        
        # 도움말
        "help"|"-h"|"--help"|"") show_help ;;
        
        *)
            log_error "알 수 없는 명령어: $command"
            echo "사용 가능한 명령어를 보려면: $0 help"
            exit 1
            ;;
    esac
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi