#!/bin/bash
# setup_domains.sh - Project Odysseus 로컬 도메인 설정 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 함수들
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              🌐 Project Odysseus                          ║"
    echo "║           로컬 도메인 설정 스크립트                        ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 도메인 목록 정의
DOMAINS=(
    "odysseus.local"           # 메인 트레이딩 대시보드
    "grafana.odysseus.local"   # Grafana 모니터링
    "jupyter.odysseus.local"   # Jupyter Lab 분석
    "prometheus.odysseus.local" # Prometheus 메트릭
    "adminer.odysseus.local"   # 데이터베이스 관리
    "redis.odysseus.local"     # Redis 관리
    "dev.odysseus.local"       # 개발 환경
    "mailhog.odysseus.local"   # 이메일 테스트 (개발용)
    "status.odysseus.local"    # Nginx 상태
)

# hosts 파일 경로 감지
get_hosts_file() {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "C:/Windows/System32/drivers/etc/hosts"
    else
        echo "/etc/hosts"
    fi
}

# 기존 Odysseus 도메인 제거
cleanup_existing_domains() {
    local hosts_file=$(get_hosts_file)
    
    log_info "기존 Odysseus 도메인 정리 중..."
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        powershell -Command "
            \$content = Get-Content '$hosts_file' | Where-Object { \$_ -notmatch 'odysseus\.local' }
            Set-Content -Path '$hosts_file' -Value \$content
        "
    else
        # Linux/macOS
        if command -v sudo &> /dev/null; then
            sudo sed -i.backup '/odysseus\.local/d' "$hosts_file"
        else
            log_error "sudo 권한이 필요합니다"
            return 1
        fi
    fi
    
    log_success "기존 도메인 정리 완료"
}

# 새 도메인 추가
add_domains() {
    local hosts_file=$(get_hosts_file)
    
    log_info "새 도메인들을 hosts 파일에 추가 중..."
    
    # 추가할 내용 생성
    local hosts_content=""
    hosts_content+="\n# Project Odysseus Local Domains - Auto Generated $(date)\n"
    
    for domain in "${DOMAINS[@]}"; do
        hosts_content+="127.0.0.1    $domain\n"
    done
    
    hosts_content+="# End of Project Odysseus Domains\n"
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        powershell -Command "
            Add-Content -Path '$hosts_file' -Value '$hosts_content'
        "
    else
        # Linux/macOS
        if command -v sudo &> /dev/null; then
            echo -e "$hosts_content" | sudo tee -a "$hosts_file" > /dev/null
        else
            log_error "sudo 권한이 필요합니다"
            return 1
        fi
    fi
    
    log_success "도메인 추가 완료"
}

# 도메인 검증
verify_domains() {
    log_info "도메인 설정 검증 중..."
    
    for domain in "${DOMAINS[@]}"; do
        if nslookup "$domain" > /dev/null 2>&1; then
            if nslookup "$domain" | grep -q "127.0.0.1"; then
                echo "✅ $domain → 127.0.0.1"
            else
                log_warning "$domain이 다른 IP로 설정되어 있습니다"
            fi
        else
            log_warning "$domain 해상도 실패"
        fi
    done
}

# SSL 인증서 생성 (개발용)
generate_dev_certificates() {
    log_info "개발용 SSL 인증서 생성 중..."
    
    mkdir -p ./nginx/certs
    
    # 루트 CA 생성
    if [ ! -f ./nginx/certs/ca-key.pem ]; then
        openssl genrsa -out ./nginx/certs/ca-key.pem 4096
        openssl req -new -x509 -sha256 -days 365 -key ./nginx/certs/ca-key.pem -out ./nginx/certs/ca.pem \
            -subj "/C=KR/ST=Seoul/L=Seoul/O=Project Odysseus/OU=Development/CN=Odysseus Root CA"
    fi
    
    # 서버 인증서 생성
    if [ ! -f ./nginx/certs/server-key.pem ]; then
        openssl genrsa -out ./nginx/certs/server-key.pem 4096
        
        # SAN (Subject Alternative Names) 설정
        cat > ./nginx/certs/server.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = KR
ST = Seoul
L = Seoul
O = Project Odysseus
OU = Development
CN = odysseus.local

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = odysseus.local
DNS.2 = *.odysseus.local
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF
        
        openssl req -new -key ./nginx/certs/server-key.pem -out ./nginx/certs/server.csr -config ./nginx/certs/server.conf
        openssl x509 -req -in ./nginx/certs/server.csr -CA ./nginx/certs/ca.pem -CAkey ./nginx/certs/ca-key.pem \
            -CAcreateserial -out ./nginx/certs/server.pem -days 365 -extensions v3_req -extfile ./nginx/certs/server.conf
        
        # Nginx용 파일명으로 복사
        cp ./nginx/certs/server.pem ./nginx/certs/fullchain.pem
        cp ./nginx/certs/server-key.pem ./nginx/certs/privkey.pem
    fi
    
    log_success "개발용 SSL 인증서 생성 완료"
    log_info "브라우저에서 인증서 신뢰 설정 필요: ./nginx/certs/ca.pem"
}

# Nginx 설정 파일 생성
create_nginx_configs() {
    log_info "Nginx 추가 설정 파일들 생성 중..."
    
    mkdir -p ./nginx/conf.d
    
    # 기본 보안 설정
    cat > ./nginx/conf.d/security.conf << 'EOF'
# security.conf - 보안 강화 설정

# 서버 정보 숨기기
server_tokens off;

# 요청 크기 제한
client_max_body_size 100M;
client_body_buffer_size 16K;
client_header_buffer_size 1k;
large_client_header_buffers 2 1k;

# 타임아웃 설정
client_body_timeout 12;
client_header_timeout 12;
keepalive_timeout 15;
send_timeout 10;

# DDoS 보호
limit_req_zone $binary_remote_addr zone=global:10m rate=1r/s;
limit_conn_zone $binary_remote_addr zone=addr:10m;

# 파일 업로드 제한
client_body_in_file_only clean;
client_body_in_single_buffer on;
EOF

    # 캐싱 설정
    cat > ./nginx/conf.d/cache.conf << 'EOF'
# cache.conf - 캐싱 최적화 설정

# 정적 파일 캐싱
location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Cache "HIT";
}

# API 응답 캐싱 (선택적)
location ~* /api/(market-data|pairs)/ {
    proxy_cache_bypass $http_pragma;
    proxy_cache_revalidate on;
    proxy_cache_min_uses 1;
    proxy_cache_use_stale error timeout invalid_header updating http_500 http_502 http_503 http_504;
    expires 1m;
}
EOF

    # 로깅 설정
    cat > ./nginx/conf.d/logging.conf << 'EOF'
# logging.conf - 로깅 최적화 설정

# 액세스 로그 형식
log_format detailed '$remote_addr - $remote_user [$time_local] '
                   '"$request" $status $bytes_sent '
                   '"$http_referer" "$http_user_agent" '
                   '"$http_x_forwarded_for" '
                   'rt=$request_time uct="$upstream_connect_time" '
                   'uht="$upstream_header_time" urt="$upstream_response_time" '
                   'service="$upstream_addr"';

# 서비스별 로그 분리
map $upstream_addr $service_name {
    ~trading-bot trading-bot;
    ~grafana grafana;
    ~jupyter jupyter;
    default unknown;
}

# 조건부 로깅 (정적 파일은 로그 제외)
map $request_uri $loggable {
    ~*\.(css|js|png|jpg|jpeg|gif|ico|woff|woff2)$ 0;
    default 1;
}
EOF

    log_success "Nginx 설정 파일들 생성 완료"
}

# 방화벽 설정 (Linux만)
configure_firewall() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "방화벽 설정 중..."
        
        if command -v ufw &> /dev/null; then
            # UFW 사용
            sudo ufw --force enable
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            
            # 필요한 포트만 개방
            sudo ufw allow 22/tcp    # SSH
            sudo ufw allow 80/tcp    # HTTP
            sudo ufw allow 443/tcp   # HTTPS
            
            # Docker 서비스 포트는 차단 (리버스 프록시를 통해서만 접근)
            sudo ufw deny 3000/tcp   # Grafana 직접 접근 차단
            sudo ufw deny 8080/tcp   # Adminer 직접 접근 차단
            sudo ufw deny 8888/tcp   # Jupyter 직접 접근 차단
            
            log_success "UFW 방화벽 설정 완료"
        else
            log_warning "UFW가 설치되지 않음 - 수동으로 방화벽을 설정하세요"
        fi
    fi
}

# 메인 실행 함수
main() {
    print_banner
    
    log_info "Project Odysseus 도메인 기반 접근 환경을 설정합니다"
    echo
    
    # 관리자 권한 확인
    if [[ $EUID -eq 0 ]]; then
        log_warning "루트 권한으로 실행 중입니다"
    fi
    
    # 1. 기존 도메인 정리
    cleanup_existing_domains
    
    # 2. 새 도메인 추가
    add_domains
    
    # 3. Nginx 설정 생성
    create_nginx_configs
    
    # 4. SSL 인증서 생성 (선택적)
    read -p "개발용 SSL 인증서를 생성하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v openssl &> /dev/null; then
            generate_dev_certificates
        else
            log_error "OpenSSL이 설치되지 않았습니다"
        fi
    fi
    
    # 5. 방화벽 설정 (Linux만, 선택적)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        read -p "방화벽을 설정하시겠습니까? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            configure_firewall
        fi
    fi
    
    # 6. 도메인 검증
    verify_domains
    
    # 완료 메시지 및 사용 가이드
    echo
    log_success "🎉 도메인 설정 완료!"
    
    echo
    echo -e "${GREEN}🌐 서비스 접속 URL:${NC}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│ 🚀 메인 대시보드: http://odysseus.local                 │"
    echo "│ 📊 Grafana: http://grafana.odysseus.local               │"
    echo "│ 📓 Jupyter: http://jupyter.odysseus.local               │"
    echo "│ 🔍 Prometheus: http://prometheus.odysseus.local         │"
    echo "│ 🗃️ Adminer: http://adminer.odysseus.local               │"
    echo "│ 🔴 Redis: http://redis.odysseus.local                   │"
    echo "│ 🛠️ 개발환경: http://dev.odysseus.local                  │"
    echo "│ 📧 MailHog: http://mailhog.odysseus.local (개발용)       │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo
    
    echo -e "${BLUE}📋 다음 단계:${NC}"
    echo "1. Docker 환경 시작:"
    echo "   docker-compose -f docker-compose-enhanced.yml up -d"
    echo
    echo "2. 서비스 확인:"
    echo "   curl http://odysseus.local"
    echo "   curl http://grafana.odysseus.local"
    echo
    echo "3. 브라우저에서 접속 테스트"
    echo
    
    if [ -f ./nginx/certs/ca.pem ]; then
        echo -e "${YELLOW}🔒 SSL 인증서 신뢰 설정:${NC}"
        echo "  - Chrome/Edge: 설정 > 고급 > 인증서 관리 > 신뢰할 수 있는 루트 인증 기관"
        echo "  - Firefox: about:config > security.tls.insecure_fallback_hosts"
        echo "  - 인증서 파일: ./nginx/certs/ca.pem"
        echo
    fi
}

# 도메인 제거 함수
remove_domains() {
    log_info "Odysseus 도메인들을 제거합니다..."
    cleanup_existing_domains
    log_success "도메인 제거 완료"
}

# 상태 확인 함수
check_domains() {
    log_info "현재 도메인 설정 상태 확인 중..."
    
    local hosts_file=$(get_hosts_file)
    echo "📁 Hosts 파일: $hosts_file"
    echo
    
    if grep -q "odysseus.local" "$hosts_file" 2>/dev/null; then
        echo "🔍 현재 설정된 Odysseus 도메인들:"
        grep "odysseus.local" "$hosts_file" 2>/dev/null || echo "없음"
    else
        echo "⚠️  Odysseus 도메인이 설정되지 않았습니다"
    fi
    
    echo
    verify_domains
}

# 사용법 출력
show_usage() {
    echo "사용법: $0 <command>"
    echo
    echo "Commands:"
    echo "  setup     - 도메인 설정 (기본)"
    echo "  remove    - 도메인 제거"
    echo "  check     - 현재 상태 확인"
    echo "  verify    - 도메인 해상도 검증"
    echo
    echo "예시:"
    echo "  $0 setup    # 도메인 설정"
    echo "  $0 check    # 상태 확인"
}

# 명령어 처리
case "${1:-setup}" in
    "setup")
        main
        ;;
    "remove")
        remove_domains
        ;;
    "check")
        check_domains
        ;;
    "verify")
        verify_domains
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "알 수 없는 명령어: $1"
        show_usage
        exit 1
        ;;
esac