"""Create schemas and extensions

Revision ID: 001_schemas_extensions  
Revises: 
Create Date: 2024-01-01 00:00:00.000000

이 마이그레이션은 Project Odysseus의 기본 인프라를 설정합니다:
- PostgreSQL 확장 (TimescaleDB, UUID 등)
- 논리적 스키마 분리 (market_data, trading, analysis, monitoring)
- 기본 보안 및 권한 설정

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_schemas_extensions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """스키마 및 확장 생성"""
    
    # =================================================================
    # 1. PostgreSQL 확장 설치
    # =================================================================
    
    print("🔧 PostgreSQL 확장 설치 중...")
    
    # TimescaleDB 확장 (핵심)
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    """)
    
    # UUID 생성 확장
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    """)
    
    # 쿼리 성능 모니터링 확장
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    """)
    
    # 암호화 관련 확장 (선택적)
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    """)
    
    print("✅ PostgreSQL 확장 설치 완료")
    
    # =================================================================
    # 2. 논리적 스키마 생성
    # =================================================================
    
    print("📁 논리적 스키마 생성 중...")
    
    # 시장 데이터 스키마
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS market_data 
        COMMENT = 'Raw market data: prices, orderbook, trades';
    """)
    
    # 거래 실행 스키마  
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS trading
        COMMENT = 'Trade execution: positions, orders, executions';
    """)
    
    # 분석 결과 스키마
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS analysis
        COMMENT = 'Analysis results: pairs, signals, ML predictions';
    """)
    
    # 모니터링 스키마
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS monitoring
        COMMENT = 'System monitoring: performance, health, errors';
    """)
    
    print("✅ 스키마 생성 완료")
    
    # =================================================================
    # 3. 기본 검색 경로 설정
    # =================================================================
    
    print("🔍 기본 검색 경로 설정 중...")
    
    op.execute("""
        ALTER DATABASE odysseus_trading 
        SET search_path TO market_data, trading, analysis, monitoring, public;
    """)
    
    print("✅ 검색 경로 설정 완료")
    
    # =================================================================
    # 4. 기본 사용자 및 권한 설정 (선택적)
    # =================================================================
    
    print("👤 기본 권한 설정 중...")
    
    # 애플리케이션 사용자가 존재하지 않을 경우에만 생성
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'odysseus_app') THEN
                CREATE USER odysseus_app WITH PASSWORD 'change_me_in_production';
                COMMENT ON ROLE odysseus_app IS 'Application user for Project Odysseus';
            END IF;
        END $$;
    """)
    
    # 읽기 전용 사용자 (대시보드용)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'odysseus_readonly') THEN
                CREATE USER odysseus_readonly WITH PASSWORD 'change_me_readonly';
                COMMENT ON ROLE odysseus_readonly IS 'Read-only user for dashboards and monitoring';
            END IF;
        END $$;
    """)
    
    # 스키마 사용 권한 부여
    for schema in ['market_data', 'trading', 'analysis', 'monitoring']:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO odysseus_app;")
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO odysseus_readonly;")
    
    print("✅ 기본 권한 설정 완료")
    
    # =================================================================
    # 5. 시스템 정보 및 검증
    # =================================================================
    
    print("ℹ️ 시스템 정보 확인 중...")
    
    # TimescaleDB 버전 확인
    op.execute("""
        DO $$
        DECLARE
            ts_version TEXT;
        BEGIN
            SELECT extversion INTO ts_version 
            FROM pg_extension 
            WHERE extname = 'timescaledb';
            
            IF ts_version IS NOT NULL THEN
                RAISE NOTICE 'TimescaleDB version: %', ts_version;
            ELSE
                RAISE WARNING 'TimescaleDB extension not found!';
            END IF;
        END $$;
    """)
    
    # PostgreSQL 버전 정보
    op.execute("""
        DO $$
        DECLARE
            pg_version TEXT;
        BEGIN
            SELECT version() INTO pg_version;
            RAISE NOTICE 'PostgreSQL: %', split_part(pg_version, ' ', 2);
        END $$;
    """)
    
    print("✅ 스키마 및 확장 설정 완료!")

def downgrade() -> None:
    """스키마 및 확장 제거"""
    
    print("🗑️ 스키마 및 확장 롤백 중...")
    
    # =================================================================
    # 1. 스키마 제거 (CASCADE로 모든 객체 포함)
    # =================================================================
    
    print("📁 스키마 제거 중...")
    
    # 모든 스키마를 역순으로 제거
    schemas_to_drop = ['monitoring', 'analysis', 'trading', 'market_data']
    
    for schema in schemas_to_drop:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE;")
        print(f"✅ {schema} 스키마 제거 완료")
    
    # =================================================================
    # 2. 사용자 제거
    # =================================================================
    
    print("👤 사용자 제거 중...")
    
    # 연결 종료 후 사용자 제거
    op.execute("""
        DO $$
        BEGIN
            -- 기존 연결 종료
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE usename IN ('odysseus_app', 'odysseus_readonly') 
              AND pid <> pg_backend_pid();
            
            -- 사용자 제거
            DROP USER IF EXISTS odysseus_app;
            DROP USER IF EXISTS odysseus_readonly;
            
            RAISE NOTICE 'Application users removed';
        END $$;
    """)
    
    # =================================================================
    # 3. 확장 제거 (주의: 다른 DB에 영향 줄 수 있음)
    # =================================================================
    
    print("🔧 확장 제거 중...")
    
    # 선택적 확장들 제거
    extensions_to_drop = [
        'pg_stat_statements',
        'pgcrypto', 
        'uuid-ossp'
    ]
    
    for ext in extensions_to_drop:
        op.execute(f"DROP EXTENSION IF EXISTS \"{ext}\" CASCADE;")
    
    # TimescaleDB는 마지막에 제거 (다른 객체들이 의존할 수 있음)
    print("⚠️ TimescaleDB 확장 제거 중 (주의: 시스템 전체에 영향)")
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
    
    # =================================================================
    # 4. 검색 경로 초기화
    # =================================================================
    
    op.execute("""
        ALTER DATABASE odysseus_trading 
        SET search_path TO public;
    """)
    
    print("✅ 스키마 및 확장 롤백 완료")