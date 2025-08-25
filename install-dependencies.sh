#!/bin/bash
# install_dependencies.sh - Project Odysseus 의존성 설치 스크립트

set -e  # 오류 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 제목 출력
echo -e "${BLUE}"
echo "🚀 Project Odysseus 의존성 설치 스크립트"
echo "=============================================="
echo -e "${NC}"

# 운영체제 감지
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log_info "Linux 환경 감지"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log_info "macOS 환경 감지"
elif [[ "$OSTYPE" == "msys" ]]; then
    OS="windows"
    log_info "Windows 환경 감지"
else
    log_warning "알 수 없는 운영체제: $OSTYPE"
    OS="unknown"
fi

# Python 버전 확인
log_info "Python 버전 확인 중..."
python_version=$(python --version 2>&1 | cut -d' ' -f2)
python_major=$(echo $python_version | cut -d'.' -f1)
python_minor=$(echo $python_version | cut -d'.' -f2)

if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 10 ]; then
    log_success "Python $python_version 확인됨 (요구사항: 3.10+)"
else
    log_error "Python 3.10 이상이 필요합니다. 현재 버전: $python_version"
    exit 1
fi

# 가상환경 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    log_success "가상환경 활성화됨: $VIRTUAL_ENV"
else
    log_warning "가상환경이 활성화되지 않음"
    read -p "가상환경을 생성하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "가상환경 생성 중..."
        python -m venv odysseus_env
        
        if [[ "$OS" == "windows" ]]; then
            source odysseus_env/Scripts/activate
        else
            source odysseus_env/bin/activate
        fi
        log_success "가상환경 생성 및 활성화 완료"
    else
        log_warning "가상환경 없이 계속합니다 (권장하지 않음)"
    fi
fi

# pip 업그레이드
log_info "pip 업그레이드 중..."
python -m pip install --upgrade pip
log_success "pip 업그레이드 완료"

# 시스템별 사전 요구사항 설치
install_system_deps() {
    case $OS in
        "linux")
            log_info "Linux 시스템 의존성 설치 중..."
            
            # 패키지 매니저 감지
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y \
                    build-essential \
                    libta-lib0-dev \
                    libpq-dev \
                    python3-dev \
                    gcc \
                    g++
            elif command -v yum &> /dev/null; then
                sudo yum install -y \
                    gcc \
                    gcc-c++ \
                    ta-lib-devel \
                    postgresql-devel \
                    python3-devel
            else
                log_warning "지원되지 않는 패키지 매니저입니다. 수동으로 의존성을 설치해주세요."
            fi
            ;;
            
        "macos")
            log_info "macOS 시스템 의존성 설치 중..."
            
            if command -v brew &> /dev/null; then
                brew install ta-lib postgresql
            else
                log_error "Homebrew가 설치되지 않았습니다."
                log_info "Homebrew 설치: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
            
        "windows")
            log_warning "Windows에서는 수동으로 Visual C++ Build Tools를 설치해야 할 수 있습니다."
            log_info "다운로드: https://visualstudio.microsoft.com/visual-cpp-build-tools/"
            ;;
    esac
}

# 설치 타입 선택
echo
echo "설치 타입을 선택하세요:"
echo "1) 기본 설치 (운영용)"
echo "2) 개발 설치 (개발용 도구 포함)"
echo "3) 최소 설치 (핵심 패키지만)"

read -p "선택 (1-3): " install_type

case $install_type in
    1)
        log_info "기본 설치 모드"
        install_system_deps
        pip install -r requirements.txt
        ;;
    2)
        log_info "개발 설치 모드"
        install_system_deps
        pip install -r requirements-dev.txt
        
        # pre-commit 설정
        if command -v pre-commit &> /dev/null; then
            log_info "pre-commit hooks 설치 중..."
            pre-commit install
            log_success "pre-commit hooks 설치 완료"
        fi
        ;;
    3)
        log_info "최소 설치 모드"
        pip install pandas numpy ccxt psycopg2-binary python-dotenv loguru
        ;;
    *)
        log_error "잘못된 선택입니다."
        exit 1
        ;;
esac

# TA-Lib 별도 설치 시도
log_info "TA-Lib 설치 시도 중..."
if pip install TA-Lib; then
    log_success "TA-Lib 설치 완료"
else
    log_warning "TA-Lib 설치 실패 (선택적 패키지)"
    log_info "TA-Lib 수동 설치 가이드:"
    case $OS in
        "linux")
            echo "  sudo apt-get install libta-lib0-dev"
            echo "  pip install TA-Lib"
            ;;
        "macos")
            echo "  brew install ta-lib"
            echo "  pip install TA-Lib"
            ;;
        "windows")
            echo "  https://github.com/mrjbq7/ta-lib에서 .whl 파일 다운로드 후:"
            echo "  pip install [다운로드한_파일.whl]"
            ;;
    esac
fi

# 설치 검증
log_info "설치 검증 중..."

# 핵심 패키지 import 테스트
python -c "
import sys
packages = [
    'pandas', 'numpy', 'ccxt', 'psycopg2', 
    'loguru', 'python_dotenv', 'statsmodels'
]

failed = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError as e:
        print(f'❌ {pkg}: {e}')
        failed.append(pkg)

if failed:
    print(f'\n실패한 패키지: {failed}')
    sys.exit(1)
else:
    print('\n🎉 모든 핵심 패키지 설치 확인!')
"

if [ $? -eq 0 ]; then
    log_success "패키지 설치 및 검증 완료!"
else
    log_error "일부 패키지 설치에 실패했습니다."
    exit 1
fi

# 다음 단계 안내
echo
echo -e "${GREEN}🎉 설치 완료!${NC}"
echo
echo "다음 단계:"
echo "1. 환경 변수 설정: cp .env.example .env && nano .env"
echo "2. 데이터베이스 설정: docker-compose up -d timescaledb"
echo "3. 봇 실행: python main.py"
echo
echo "유용한 명령어들:"
echo "- 테스트 실행: pytest"
echo "- 코드 포맷팅: black ."
echo "- 코드 검사: flake8 ."
echo "- 타입 체크: mypy ."
echo "- 보안 검사: bandit -r ."
echo
echo "문제 발생시 참고사항:"
echo "- TA-Lib 설치 실패: 시스템 의존성 먼저 설치 필요"
echo "- PostgreSQL 연결 오류: Docker로 TimescaleDB 실행 확인"
echo "- 권한 오류: 가상환경 활성화 후 재시도"
echo
echo -e "${YELLOW}⚠️  중요: .env 파일에서 API 키를 반드시 설정하세요!${NC}"