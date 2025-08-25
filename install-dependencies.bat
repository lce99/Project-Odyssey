@echo off
REM install_dependencies.bat - Project Odysseus Windows 설치 스크립트
setlocal EnableDelayedExpansion

echo.
echo 🚀 Project Odysseus 의존성 설치 스크립트 (Windows)
echo ==================================================
echo.

REM Python 버전 확인
echo [정보] Python 버전 확인 중...
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았거나 PATH에 없습니다.
    echo Python 3.10 이상을 설치하세요: https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set python_version=%%i
echo [성공] Python %python_version% 감지

REM Python 버전 체크 (간단한 방식)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [오류] Python 3.10 이상이 필요합니다.
    pause
    exit /b 1
)

REM 가상환경 확인
if defined VIRTUAL_ENV (
    echo [성공] 가상환경 활성화됨: %VIRTUAL_ENV%
) else (
    echo [경고] 가상환경이 활성화되지 않음
    set /p create_venv="가상환경을 생성하시겠습니까? (y/n): "
    if /i "!create_venv!"=="y" (
        echo [정보] 가상환경 생성 중...
        python -m venv odysseus_env
        call odysseus_env\Scripts\activate.bat
        echo [성공] 가상환경 생성 및 활성화 완료
    ) else (
        echo [경고] 가상환경 없이 계속합니다 (권장하지 않음)
    )
)

REM pip 업그레이드
echo [정보] pip 업그레이드 중...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [오류] pip 업그레이드 실패
    pause
    exit /b 1
)
echo [성공] pip 업그레이드 완료

REM Visual C++ Build Tools 확인
echo [정보] Visual C++ Build Tools 확인 중...
python -c "import distutils.msvc9compiler" >nul 2>&1
if errorlevel 1 (
    echo [경고] Visual C++ Build Tools가 없을 수 있습니다.
    echo 일부 패키지 컴파일에 필요할 수 있습니다.
    echo 다운로드: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
)

REM 설치 타입 선택
echo.
echo 설치 타입을 선택하세요:
echo 1) 기본 설치 (운영용)
echo 2) 개발 설치 (개발용 도구 포함)
echo 3) 최소 설치 (핵심 패키지만)
echo.

set /p install_type="선택 (1-3): "

if "%install_type%"=="1" (
    echo [정보] 기본 설치 모드
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 기본 패키지 설치 실패
        pause
        exit /b 1
    )
) else if "%install_type%"=="2" (
    echo [정보] 개발 설치 모드
    pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [오류] 개발 패키지 설치 실패
        pause
        exit /b 1
    )
    
    REM pre-commit 설정
    where pre-commit >nul 2>&1
    if not errorlevel 1 (
        echo [정보] pre-commit hooks 설치 중...
        pre-commit install
        echo [성공] pre-commit hooks 설치 완료
    )
) else if "%install_type%"=="3" (
    echo [정보] 최소 설치 모드
    pip install pandas numpy ccxt psycopg2-binary python-dotenv loguru
    if errorlevel 1 (
        echo [오류] 최소 패키지 설치 실패
        pause
        exit /b 1
    )
) else (
    echo [오류] 잘못된 선택입니다.
    pause
    exit /b 1
)

REM TA-Lib 설치 시도
echo [정보] TA-Lib 설치 시도 중...
pip install TA-Lib >nul 2>&1
if errorlevel 1 (
    echo [경고] TA-Lib 설치 실패 (선택적 패키지)
    echo.
    echo TA-Lib 수동 설치 방법:
    echo 1. https://github.com/mrjbq7/ta-lib/releases 방문
    echo 2. Python 버전에 맞는 .whl 파일 다운로드
    echo 3. pip install [다운로드한_파일.whl]
    echo.
) else (
    echo [성공] TA-Lib 설치 완료
)

REM 설치 검증
echo [정보] 설치 검증 중...

python -c "
import sys
packages = [
    'pandas', 'numpy', 'ccxt', 'psycopg2', 
    'loguru', 'dotenv', 'statsmodels'
]

failed = []
for pkg in packages:
    try:
        if pkg == 'dotenv':
            __import__('python_dotenv')
        else:
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

if errorlevel 1 (
    echo [오류] 일부 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

REM 완료 메시지
echo.
echo 🎉 설치 완료!
echo.
echo 다음 단계:
echo 1. 환경 변수 설정: copy .env.example .env
echo 2. .env 파일을 편집하여 API 키 등을 설정
echo 3. 데이터베이스 설정: docker-compose up -d timescaledb
echo 4. 봇 실행: python main.py
echo.
echo 유용한 명령어들:
echo - 테스트 실행: pytest
echo - 코드 포맷팅: black .
echo - 코드 검사: flake8 .
echo - 타입 체크: mypy .
echo.
echo 문제 발생시:
echo - 관리자 권한으로 실행 시도
echo - Python과 pip 버전 확인
echo - Visual C++ Build Tools 설치
echo.
echo ⚠️ 중요: .env 파일에서 API 키를 반드시 설정하세요!

pause