
# =============================================================================
# 008 - TimescaleDB 정책 및 최종 설정
# =============================================================================

"""Setup TimescaleDB policies and final configurations

Revision ID: 008_timescaledb_policies
Revises: 007_views_functions
Create Date: 2024-01-01 00:07:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '008_timescaledb_policies'
down_revision = '007_views_functions'  
branch_labels = None
depends_on = None

def get_env_policies():
    """환경별 정책 가져오기"""
    from alembic import context
    return getattr(context, '_env_policies', {
        'price_data_retention': 'INTERVAL \'6 months\'',
        'orderbook_retention': 'INTERVAL \'1 month\'',
        'analysis_retention': 'INTERVAL \'1 year\'',
    })

def upgrade() -> None:
    """TimescaleDB 데이터 보존 정책 및 최종 설정"""
    
    print("🕐 TimescaleDB 정책 및 최종 설정 적용 중...")
    
    policies = get_env_policies()
    
    # =================================================================
    # 1. 데이터 보존 정책 (환경별 차등)
    # =================================================================
    
    print("🗂️ 데이터 보존 정책 적용 중...")
    
    # 가격 데이터 보존 정책
    price_retention = policies.get('price_data_retention', 'INTERVAL \'6 months\'')
    op.execute(f"""
        SELECT add_retention_policy('market_data.price_data', {price_retention});
    """)
    
    # 오더북 데이터 보존 정책 (단기)
    orderbook_retention = policies.get('orderbook_retention', 'INTERVAL \'1 month\'')
    op.execute(f"""
        SELECT add_retention_policy('market_data.orderbook_data', {orderbook_retention});
    """)
    
    # 분석 결과 보존 정책
    analysis_retention = policies.get('analysis_retention', 'INTERVAL \'1 year\'')
    for table in ['kalman_states', 'market_regime_filters', 'ml_predictions', 'signals']:
        op.execute(f"""
            SELECT add_retention_policy('analysis.{table}', {analysis_retention});
        """)
    
    # 거래 실행 로그 보존 정책
    op.execute("""
        SELECT add_retention_policy('trading.order_executions', INTERVAL '3 years');
    """)
    
    # 시스템 로그 보존 정책  
    op.execute("""
        SELECT add_retention_policy('monitoring.system_health', INTERVAL '3 months');
        SELECT add_retention_policy('monitoring.error_logs', INTERVAL '6 months');
    """)
    
    print("✅ 데이터 보존 정책 적용 완료")
    
    # =================================================================
    # 2. 연속 집계 (Continuous Aggregates) 설정
    # =================================================================
    
    print("📊 연속 집계 뷰 생성 중...")
    
    # 시간별 거래 성과 집계
    op.execute("""
        CREATE MATERIALIZED VIEW monitoring.hourly_performance
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('1 hour', execution_time) AS hour,
            COUNT(*) as trade_count,
            SUM(net_pnl_usd) as total_pnl,
            AVG(net_pnl_usd) as avg_pnl,
            COUNT(*) FILTER (WHERE net_pnl_usd > 0) as winning_trades
        FROM trading.trades
        WHERE trade_type = 'CLOSE'
        GROUP BY hour;
    """)
    
    # 페어별 일별 Z-score 통계
    op.execute("""
        CREATE MATERIALIZED VIEW analysis.daily_pair_stats
        WITH (timescaledb.continuous) AS
        SELECT 
            time_bucket('1 day', time) AS day,
            pair_id,
            AVG(z_score) as avg_z_score,
            MAX(ABS(z_score)) as max_abs_z_score,
            STDDEV(z_score) as z_score_volatility,
            COUNT(*) as data_points
        FROM analysis.kalman_states
        GROUP BY day, pair_id;
    """)
    
    # 연속 집계 새로고침 정책
    op.execute("""
        SELECT add_continuous_aggregate_policy('monitoring.hourly_performance',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '30 minutes');
    """)
    
    op.execute("""
        SELECT add_continuous_aggregate_policy('analysis.daily_pair_stats', 
            start_offset => INTERVAL '2 days',
            end_offset => INTERVAL '1 day', 
            schedule_interval => INTERVAL '1 hour');
    """)
    
    print("✅ 연속 집계 설정 완료")
    
    # =================================================================
    # 3. 통계 및 성능 모니터링 뷰
    # =================================================================
    
    print("📈 성능 모니터링 뷰 생성 중...")
    
    # 테이블 크기 모니터링 뷰
    op.execute("""
        CREATE VIEW monitoring.table_sizes AS
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
        FROM pg_tables 
        WHERE schemaname IN ('market_data', 'trading', 'analysis', 'monitoring')
        ORDER BY size_bytes DESC;
    """)
    
    # TimescaleDB 청크 정보 뷰
    op.execute("""
        CREATE VIEW monitoring.timescaledb_chunks AS
        SELECT 
            hypertable_name,
            chunk_name,
            pg_size_pretty(total_bytes) as chunk_size,
            range_start,
            range_end,
            is_compressed
        FROM timescaledb_information.chunks
        WHERE hypertable_schema IN ('market_data', 'trading', 'analysis', 'monitoring')
        ORDER BY range_start DESC;
    """)
    
    # =================================================================
    # 4. 최종 권한 및 보안 설정
    # =================================================================
    
    print("🔐 최종 보안 설정 적용 중...")
    
    # 연속 집계 뷰 권한
    op.execute("""
        GRANT SELECT ON monitoring.hourly_performance TO odysseus_app, odysseus_readonly;
        GRANT SELECT ON analysis.daily_pair_stats TO odysseus_app, odysseus_readonly;
    """)
    
    # 모니터링 뷰 권한
    op.execute("""
        GRANT SELECT ON monitoring.table_sizes TO odysseus_app, odysseus_readonly;
        GRANT SELECT ON monitoring.timescaledb_chunks TO odysseus_app, odysseus_readonly;
    """)
    
    # Row Level Security 활성화 (고급 보안)
    op.execute("""
        -- 민감한 테이블에 RLS 적용 (필요시)
        -- ALTER TABLE trading.positions ENABLE ROW LEVEL SECURITY;
        -- CREATE POLICY positions_policy ON trading.positions FOR ALL TO odysseus_app USING (true);
    """)
    
    # =================================================================
    # 5. 시스템 정보 및 검증
    # =================================================================
    
    print("ℹ️ 최종 시스템 정보 확인 중...")
    
    op.execute("""
        DO $
        DECLARE
            hypertable_count INTEGER;
            compression_policy_count INTEGER;  
            retention_policy_count INTEGER;
            aggregate_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO hypertable_count 
            FROM timescaledb_information.hypertables 
            WHERE hypertable_schema IN ('market_data', 'trading', 'analysis', 'monitoring');
            
            SELECT COUNT(*) INTO compression_policy_count
            FROM timescaledb_information.compression_settings
            WHERE hypertable_schema IN ('market_data', 'trading', 'analysis', 'monitoring');
            
            SELECT COUNT(*) INTO retention_policy_count  
            FROM timescaledb_information.drop_chunks_policies
            WHERE hypertable_schema IN ('market_data', 'trading', 'analysis', 'monitoring');
            
            SELECT COUNT(*) INTO aggregate_count
            FROM timescaledb_information.continuous_aggregates
            WHERE hypertable_schema IN ('market_data', 'trading', 'analysis', 'monitoring');
            
            RAISE NOTICE '=== Project Odysseus Database Setup Complete ===';
            RAISE NOTICE 'Hypertables: %', hypertable_count;
            RAISE NOTICE 'Compression Policies: %', compression_policy_count;  
            RAISE NOTICE 'Retention Policies: %', retention_policy_count;
            RAISE NOTICE 'Continuous Aggregates: %', aggregate_count;
            RAISE NOTICE '===============================================';
        END $;
    """)
    
    print("🎉 Project Odysseus 데이터베이스 설정 완료!")

def downgrade() -> None:
    """TimescaleDB 정책 및 설정 제거"""
    
    print("🗑️ TimescaleDB 정책 제거 중...")
    
    # 연속 집계 정책 제거
    op.execute("""
        SELECT remove_continuous_aggregate_policy('monitoring.hourly_performance', if_not_exists => true);
        SELECT remove_continuous_aggregate_policy('analysis.daily_pair_stats', if_not_exists => true);
    """)
    
    # 연속 집계 뷰 제거
    op.execute("DROP MATERIALIZED VIEW IF EXISTS monitoring.hourly_performance;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analysis.daily_pair_stats;")
    
    # 모니터링 뷰 제거
    op.execute("DROP VIEW IF EXISTS monitoring.timescaledb_chunks;")
    op.execute("DROP VIEW IF EXISTS monitoring.table_sizes;")
    
    # 보존 정책 제거
    tables_with_retention = [
        'market_data.price_data',
        'market_data.orderbook_data', 
        'analysis.kalman_states',
        'analysis.market_regime_filters',
        'analysis.ml_predictions',
        'analysis.signals',
        'trading.order_executions',
        'monitoring.system_health',
        'monitoring.error_logs'
    ]
    
    for table in tables_with_retention:
        op.execute(f"SELECT remove_retention_policy('{table}', if_not_exists => true);")
    
    print("✅ TimescaleDB 정책 롤백 완료")

# =============================================================================
# 마이그레이션 실행 가이드 및 검증 스크립트
# =============================================================================

MIGRATION_EXECUTION_GUIDE = '''
# Project Odysseus - Alembic 마이그레이션 실행 가이드

## 1. 실행 순서 (중요!)

```bash
# 1. 환경 설정
cp .env.12factor .env
nano .env  # 실제 데이터베이스 정보 입력

# 2. Alembic 환경 설정 
./setup_alembic.sh

# 3. 마이그레이션 순차 실행
alembic upgrade 001_schemas_extensions
alembic upgrade 002_market_data_tables  
alembic upgrade 003_analysis_tables
alembic upgrade 004_trading_tables
alembic upgrade 005_monitoring_tables
alembic upgrade 006_indexes_constraints
alembic upgrade 007_views_functions
alembic upgrade 008_timescaledb_policies

# 또는 한 번에 실행
alembic upgrade head
```

## 2. 검증 쿼리

```sql
-- 하이퍼테이블 확인
SELECT hypertable_name, hypertable_schema 
FROM timescaledb_information.hypertables;

-- 압축 정책 확인
SELECT hypertable_name, compress_after 
FROM timescaledb_information.compression_settings;

-- 보존 정책 확인  
SELECT hypertable_name, drop_after
FROM timescaledb_information.drop_chunks_policies;

-- 테이블 크기 확인
SELECT * FROM monitoring.table_sizes;

-- 시스템 대시보드 테스트
SELECT * FROM monitoring.system_dashboard;
```

## 3. 롤백 (긴급시)

```bash
# 전체 롤백
alembic downgrade base

# 단계별 롤백  
alembic downgrade 007_views_functions
alembic downgrade 006_indexes_constraints
# ... 역순으로 진행
```

## 4. 트러블슈팅

### 문제: TimescaleDB 확장 오류
```sql
-- 수동 확장 설치
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

### 문제: 권한 오류
```bash
# PostgreSQL superuser로 실행
sudo -u postgres psql -d odysseus_trading -f migration_file.sql
```

### 문제: 메모리 부족
```bash
# shared_buffers 조정
ALTER SYSTEM SET shared_buffers = '256MB';
SELECT pg_reload_conf();
```
'''

print("📋 Alembic 마이그레이션 스크립트 생성 완료!")
print(MIGRATION_EXECUTION_GUIDE)