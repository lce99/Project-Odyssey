"""Create monitoring tables

Revision ID: 005_monitoring_tables
Revises: 004_trading_tables
Create Date: 2024-01-01 00:04:00.000000

성과 추적 및 시스템 모니터링을 위한 테이블들을 생성합니다:
- daily_performance: 일별 성과 집계
- pair_performance: 페어별 성과 추적
- system_health: 시스템 상태 모니터링
- error_logs: 에러 및 예외 로그

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_monitoring_tables'
down_revision = '004_trading_tables'
branch_labels = None
depends_on = None

def get_env_policies():
    """환경별 정책 가져오기"""
    from alembic import context
    return getattr(context, '_env_policies', {
        'compression_after': 'INTERVAL \'7 days\'',
    })

def upgrade() -> None:
    """모니터링 테이블 생성"""
    
    print("📊 모니터링 테이블 생성 중...")
    
    # =================================================================
    # 1. daily_performance 테이블 생성 (일별 성과 집계)
    # =================================================================
    
    print("📅 daily_performance 테이블 생성 중...")
    
    op.create_table(
        'daily_performance',
        # Primary Key (날짜)
        sa.Column('date', sa.Date, nullable=False,
                  comment='집계 기준 날짜'),
        
        # 전체 포트폴리오 성과
        sa.Column('total_pnl_usd', sa.Numeric(15, 4), nullable=False, server_default='0',
                  comment='일일 총 손익 (USD)'),
        sa.Column('total_pnl_pct', sa.Numeric(8, 4), nullable=False, server_default='0',
                  comment='일일 총 손익률'),
        sa.Column('cumulative_pnl_usd', sa.Numeric(18, 4), nullable=False, server_default='0',
                  comment='누적 손익 (USD)'),
        sa.Column('cumulative_pnl_pct', sa.Numeric(8, 4), nullable=False, server_default='0',
                  comment='누적 손익률'),
        
        # 거래 통계
        sa.Column('trades_opened', sa.Integer, nullable=False, server_default='0',
                  comment='당일 시작된 거래 수'),
        sa.Column('trades_closed', sa.Integer, nullable=False, server_default='0',
                  comment='당일 완료된 거래 수'),
        sa.Column('winning_trades', sa.Integer, nullable=False, server_default='0',
                  comment='수익 거래 수'),
        sa.Column('losing_trades', sa.Integer, nullable=False, server_default='0',
                  comment='손실 거래 수'),
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=False, server_default='0',
                  comment='승률 (%)'),
        
        # 포지션 통계
        sa.Column('avg_position_size_usd', sa.Numeric(12, 2), nullable=True,
                  comment='평균 포지션 크기 (USD)'),
        sa.Column('max_position_size_usd', sa.Numeric(12, 2), nullable=True,
                  comment='최대 포지션 크기 (USD)'),
        sa.Column('avg_holding_days', sa.Numeric(6, 2), nullable=True,
                  comment='평균 보유 기간 (일)'),
        sa.Column('max_positions_held', sa.Integer, nullable=False, server_default='0',
                  comment='동시 최대 보유 포지션 수'),
        
        # 리스크 메트릭
        sa.Column('daily_var_95', sa.Numeric(10, 4), nullable=True,
                  comment='일일 VaR (95% 신뢰구간)'),
        sa.Column('max_drawdown_pct', sa.Numeric(8, 4), nullable=True,
                  comment='최대 낙폭 (%)'),
        sa.Column('sharpe_ratio', sa.Numeric(8, 4), nullable=True,
                  comment='샤프 비율 (연환산)'),
        
        # 실행 품질
        sa.Column('avg_slippage_bps', sa.Numeric(6, 2), nullable=True,
                  comment='평균 슬리피지 (bps)'),
        sa.Column('total_fees_usd', sa.Numeric(10, 4), nullable=True,
                  comment='당일 총 수수료 (USD)'),
        
        # 시장 데이터
        sa.Column('market_total_volume_usd', sa.Numeric(20, 2), nullable=True,
                  comment='시장 전체 거래량 (USD)'),
        sa.Column('active_pairs_count', sa.Integer, nullable=False, server_default='0',
                  comment='활성 페어 수'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('date'),
        sa.CheckConstraint('trades_opened >= 0', name='non_negative_trades_opened'),
        sa.CheckConstraint('trades_closed >= 0', name='non_negative_trades_closed'),
        sa.CheckConstraint('winning_trades >= 0', name='non_negative_winning_trades'),
        sa.CheckConstraint('losing_trades >= 0', name='non_negative_losing_trades'),
        sa.CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='valid_win_rate'),
        sa.CheckConstraint('avg_position_size_usd > 0 OR avg_position_size_usd IS NULL', 
                          name='positive_avg_position_size'),
        sa.CheckConstraint('max_positions_held >= 0', name='non_negative_max_positions'),
        sa.CheckConstraint('active_pairs_count >= 0', name='non_negative_active_pairs'),
        
        schema='monitoring',
        comment='일별 거래 성과 및 통계 집계'
    )
    
    # =================================================================
    # 2. pair_performance 테이블 생성 (페어별 성과)
    # =================================================================
    
    print("👫 pair_performance 테이블 생성 중...")
    
    op.create_table(
        'pair_performance',
        # 복합 Primary Key (날짜 + 페어)
        sa.Column('date', sa.Date, nullable=False,
                  comment='집계 기준 날짜'),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        
        # 페어별 손익
        sa.Column('pnl_usd', sa.Numeric(12, 4), nullable=False, server_default='0',
                  comment='페어 일일 손익 (USD)'),
        sa.Column('pnl_pct', sa.Numeric(8, 4), nullable=False, server_default='0',
                  comment='페어 일일 손익률 (%)'),
        sa.Column('cumulative_pnl_usd', sa.Numeric(15, 4), nullable=False, server_default='0',
                  comment='페어 누적 손익 (USD)'),
        
        # 거래 통계
        sa.Column('trades_count', sa.Integer, nullable=False, server_default='0',
                  comment='당일 거래 수'),
        sa.Column('avg_trade_duration_hours', sa.Numeric(8, 2), nullable=True,
                  comment='평균 거래 지속시간 (시간)'),
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=False, server_default='0',
                  comment='페어별 승률 (%)'),
        
        # 페어별 메트릭
        sa.Column('avg_z_score_entry', sa.Numeric(6, 3), nullable=True,
                  comment='평균 진입 Z-score'),
        sa.Column('avg_z_score_exit', sa.Numeric(6, 3), nullable=True,
                  comment='평균 청산 Z-score'),
        sa.Column('correlation', sa.Numeric(6, 4), nullable=True,
                  comment='당일 상관관계'),
        sa.Column('cointegration_stability', sa.Numeric(6, 4), nullable=True,
                  comment='공적분 관계 안정성'),
        
        # 리스크 메트릭
        sa.Column('max_z_score_reached', sa.Numeric(8, 4), nullable=True,
                  comment='당일 최대 Z-score'),
        sa.Column('volatility', sa.Numeric(8, 6), nullable=True,
                  comment='페어 변동성'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('date', 'pair_id'),
        sa.CheckConstraint('trades_count >= 0', name='non_negative_trades_count'),
        sa.CheckConstraint('avg_trade_duration_hours > 0 OR avg_trade_duration_hours IS NULL',
                          name='positive_avg_duration'),
        sa.CheckConstraint('win_rate >= 0 AND win_rate <= 100', name='valid_pair_win_rate'),
        sa.CheckConstraint('correlation >= -1 AND correlation <= 1 OR correlation IS NULL',
                          name='valid_correlation'),
        sa.CheckConstraint('cointegration_stability >= 0 AND cointegration_stability <= 1 OR cointegration_stability IS NULL',
                          name='valid_cointegration_stability'),
        sa.CheckConstraint('volatility >= 0 OR volatility IS NULL', name='non_negative_volatility'),
        
        schema='monitoring',
        comment='페어별 일일 성과 및 메트릭'
    )
    
    # 외래키 제약 조건
    op.create_foreign_key(
        'fk_pair_performance_pair_id',
        'pair_performance', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='monitoring', referent_schema='analysis'
    )
    
    # =================================================================
    # 3. system_health 테이블 생성 (시스템 상태 모니터링)
    # =================================================================
    
    print("🏥 system_health 테이블 생성 중...")
    
    op.create_table(
        'system_health',
        # 시간 (파티셔닝 키)
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='헬스체크 시간'),
        
        # 데이터 수집 상태
        sa.Column('data_collection_status', sa.String(10), nullable=True,
                  comment='데이터 수집 상태'),
        sa.Column('price_data_delay_seconds', sa.Integer, nullable=True,
                  comment='가격 데이터 지연 시간(초)'),
        sa.Column('last_price_update', postgresql.TIMESTAMP(timezone=True), nullable=True,
                  comment='마지막 가격 업데이트 시간'),
        
        # 분석 엔진 상태
        sa.Column('analysis_engine_status', sa.String(10), nullable=True,
                  comment='분석 엔진 상태'),
        sa.Column('kalman_filter_errors_count', sa.Integer, nullable=False, server_default='0',
                  comment='칼만 필터 에러 수'),
        sa.Column('ml_model_prediction_errors', sa.Integer, nullable=False, server_default='0',
                  comment='ML 모델 예측 에러 수'),
        
        # 거래 실행 상태
        sa.Column('execution_engine_status', sa.String(10), nullable=True,
                  comment='거래 실행 엔진 상태'),
        sa.Column('order_success_rate', sa.Numeric(5, 2), nullable=True,
                  comment='주문 성공률 (%)'),
        sa.Column('avg_order_execution_time_ms', sa.Integer, nullable=True,
                  comment='평균 주문 실행 시간 (ms)'),
        
        # 시스템 리소스
        sa.Column('cpu_usage_pct', sa.Numeric(5, 2), nullable=True,
                  comment='CPU 사용률 (%)'),
        sa.Column('memory_usage_pct', sa.Numeric(5, 2), nullable=True,
                  comment='메모리 사용률 (%)'),
        sa.Column('disk_usage_pct', sa.Numeric(5, 2), nullable=True,
                  comment='디스크 사용률 (%)'),
        
        # 네트워크 상태
        sa.Column('exchange_api_latency_ms', sa.Integer, nullable=True,
                  comment='거래소 API 지연시간 (ms)'),
        sa.Column('exchange_api_errors_count', sa.Integer, nullable=False, server_default='0',
                  comment='거래소 API 에러 수'),
        
        # 알림 상태
        sa.Column('telegram_notifications_sent', sa.Integer, nullable=False, server_default='0',
                  comment='전송된 텔레그램 알림 수'),
        sa.Column('telegram_notification_errors', sa.Integer, nullable=False, server_default='0',
                  comment='텔레그램 알림 에러 수'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.CheckConstraint("data_collection_status IN ('HEALTHY', 'WARNING', 'ERROR') OR data_collection_status IS NULL",
                          name='valid_data_collection_status'),
        sa.CheckConstraint("analysis_engine_status IN ('HEALTHY', 'WARNING', 'ERROR') OR analysis_engine_status IS NULL",
                          name='valid_analysis_engine_status'),
        sa.CheckConstraint("execution_engine_status IN ('HEALTHY', 'WARNING', 'ERROR') OR execution_engine_status IS NULL",
                          name='valid_execution_engine_status'),
        sa.CheckConstraint('price_data_delay_seconds >= 0 OR price_data_delay_seconds IS NULL',
                          name='non_negative_price_delay'),
        sa.CheckConstraint('order_success_rate >= 0 AND order_success_rate <= 100 OR order_success_rate IS NULL',
                          name='valid_order_success_rate'),
        sa.CheckConstraint('cpu_usage_pct >= 0 AND cpu_usage_pct <= 100 OR cpu_usage_pct IS NULL',
                          name='valid_cpu_usage'),
        sa.CheckConstraint('memory_usage_pct >= 0 AND memory_usage_pct <= 100 OR memory_usage_pct IS NULL',
                          name='valid_memory_usage'),
        sa.CheckConstraint('disk_usage_pct >= 0 AND disk_usage_pct <= 100 OR disk_usage_pct IS NULL',
                          name='valid_disk_usage'),
        sa.CheckConstraint('exchange_api_latency_ms >= 0 OR exchange_api_latency_ms IS NULL',
                          name='non_negative_api_latency'),
        
        schema='monitoring',
        comment='시스템 상태 및 헬스체크 정보'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 system_health를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'monitoring.system_health', 
            'time',
            chunk_time_interval => INTERVAL '6 hours'
        );
    """)
    
    # =================================================================
    # 4. error_logs 테이블 생성 (에러 및 예외 로그)
    # =================================================================
    
    print("🚨 error_logs 테이블 생성 중...")
    
    op.create_table(
        'error_logs',
        # Primary Key
        sa.Column('error_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='에러 고유 ID'),
        
        # 시간 (파티셔닝 키)
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='에러 발생 시간'),
        
        # 에러 분류
        sa.Column('error_level', sa.String(10), nullable=False,
                  comment='에러 레벨'),
        sa.Column('error_category', sa.String(20), nullable=False,
                  comment='에러 카테고리'),
        sa.Column('error_code', sa.String(20), nullable=True,
                  comment='에러 코드'),
        
        # 에러 내용
        sa.Column('error_message', sa.Text, nullable=False,
                  comment='에러 메시지'),
        sa.Column('error_details', postgresql.JSONB, nullable=True,
                  comment='구조화된 에러 세부정보'),
        sa.Column('stack_trace', sa.Text, nullable=True,
                  comment='스택 트레이스'),
        
        # 관련 정보 (외래키)
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='관련 페어 ID'),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='관련 거래 ID'),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='관련 포지션 ID'),
        
        # 에러 상태 관리
        sa.Column('is_resolved', sa.Boolean, nullable=False, server_default='false',
                  comment='해결 여부'),
        sa.Column('resolved_at', postgresql.TIMESTAMP(timezone=True), nullable=True,
                  comment='해결 일시'),
        sa.Column('resolution_notes', sa.Text, nullable=True,
                  comment='해결 방법 메모'),
        
        # 시스템 정보
        sa.Column('module_name', sa.String(50), nullable=True,
                  comment='에러 발생 모듈'),
        sa.Column('function_name', sa.String(50), nullable=True,
                  comment='에러 발생 함수'),
        sa.Column('server_name', sa.String(20), nullable=True,
                  comment='서버 이름'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('error_id'),
        sa.CheckConstraint("error_level IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
                          name='valid_error_level'),
        sa.CheckConstraint("error_category IN ('DATA_COLLECTION', 'ANALYSIS', 'EXECUTION', 'SYSTEM', 'NETWORK', 'API')",
                          name='valid_error_category'),
        sa.CheckConstraint('resolved_at IS NULL OR resolved_at >= time',
                          name='resolved_after_occurrence'),
        
        schema='monitoring',
        comment='시스템 에러 및 예외 로그'
    )
    
    # 외래키 제약 조건들
    op.create_foreign_key(
        'fk_error_logs_pair_id',
        'error_logs', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='monitoring', referent_schema='analysis'
    )
    
    op.create_foreign_key(
        'fk_error_logs_trade_id',
        'error_logs', 'trades',
        ['trade_id'], ['trade_id'],
        source_schema='monitoring', referent_schema='trading'
    )
    
    op.create_foreign_key(
        'fk_error_logs_position_id',
        'error_logs', 'positions',
        ['position_id'], ['position_id'],
        source_schema='monitoring', referent_schema='trading'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 error_logs를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'monitoring.error_logs', 
            'time',
            chunk_time_interval => INTERVAL '1 day'
        );
    """)
    
    # =================================================================
    # 5. 인덱스 생성 (모니터링 쿼리 최적화)
    # =================================================================
    
    print("🔍 모니터링 테이블 인덱스 생성 중...")
    
    # daily_performance 인덱스
    op.execute("""
        CREATE INDEX idx_daily_performance_date_desc 
        ON monitoring.daily_performance (date DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_daily_performance_pnl 
        ON monitoring.daily_performance (date DESC, total_pnl_usd DESC);
    """)
    
    # pair_performance 인덱스
    op.execute("""
        CREATE INDEX idx_pair_performance_date_pair 
        ON monitoring.pair_performance (date DESC, pair_id);
    """)
    
    op.execute("""
        CREATE INDEX idx_pair_performance_pnl 
        ON monitoring.pair_performance (date DESC, pnl_usd DESC);
    """)
    
    # system_health 인덱스
    op.execute("""
        CREATE INDEX idx_system_health_time_status 
        ON monitoring.system_health (time DESC, data_collection_status, analysis_engine_status, execution_engine_status);
    """)
    
    op.execute("""
        CREATE INDEX idx_system_health_errors 
        ON monitoring.system_health (time DESC)
        WHERE kalman_filter_errors_count > 0 OR ml_model_prediction_errors > 0 OR exchange_api_errors_count > 0;
    """)
    
    # error_logs 핵심 인덱스들
    op.execute("""
        CREATE INDEX idx_error_logs_time_level 
        ON monitoring.error_logs (time DESC, error_level);
    """)
    
    op.execute("""
        CREATE INDEX idx_error_logs_category_time 
        ON monitoring.error_logs (error_category, time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_error_logs_unresolved 
        ON monitoring.error_logs (time DESC, error_level)
        WHERE is_resolved = FALSE;
    """)
    
    op.execute("""
        CREATE INDEX idx_error_logs_critical 
        ON monitoring.error_logs (time DESC)
        WHERE error_level = 'CRITICAL';
    """)
    
    # JSONB 인덱스 (error_details)
    op.execute("""
        CREATE INDEX idx_error_logs_details_gin 
        ON monitoring.error_logs USING GIN (error_details);
    """)
    
    # =================================================================
    # 6. 압축 정책 적용
    # =================================================================
    
    print("🗜️ 모니터링 테이블 압축 정책 적용 중...")
    
    policies = get_env_policies()
    compression_after = policies.get('compression_after', 'INTERVAL \'7 days\'')
    
    # system_health 압축 (빠른 압축)
    op.execute(f"""
        SELECT add_compression_policy(
            'monitoring.system_health', 
            INTERVAL '1 day'
        );
    """)
    
    # error_logs 압축
    op.execute(f"""
        SELECT add_compression_policy(
            'monitoring.error_logs', 
            {compression_after}
        );
    """)
    
    print("✅ 압축 정책 적용 완료")
    
    # =================================================================
    # 7. 자동 집계 트리거 함수 생성
    # =================================================================
    
    print("⚡ 자동 집계 트리거 함수 생성 중...")
    
    # 일별 성과 자동 업데이트 함수
    op.execute("""
        CREATE OR REPLACE FUNCTION monitoring.update_daily_performance_on_trade()
        RETURNS TRIGGER AS $
        DECLARE
            trade_date DATE := DATE(NEW.execution_time);
            is_winning_trade BOOLEAN := (NEW.net_pnl_usd > 0);
        BEGIN
            -- CLOSE 거래에 대해서만 집계 업데이트
            IF NEW.trade_type = 'CLOSE' THEN
                INSERT INTO monitoring.daily_performance (
                    date, 
                    total_pnl_usd, 
                    trades_closed, 
                    winning_trades, 
                    losing_trades
                ) VALUES (
                    trade_date,
                    COALESCE(NEW.net_pnl_usd, 0),
                    1,
                    CASE WHEN is_winning_trade THEN 1 ELSE 0 END,
                    CASE WHEN is_winning_trade THEN 0 ELSE 1 END
                )
                ON CONFLICT (date) DO UPDATE SET
                    total_pnl_usd = monitoring.daily_performance.total_pnl_usd + COALESCE(NEW.net_pnl_usd, 0),
                    trades_closed = monitoring.daily_performance.trades_closed + 1,
                    winning_trades = monitoring.daily_performance.winning_trades + CASE WHEN is_winning_trade THEN 1 ELSE 0 END,
                    losing_trades = monitoring.daily_performance.losing_trades + CASE WHEN is_winning_trade THEN 0 ELSE 1 END,
                    win_rate = CASE 
                        WHEN (monitoring.daily_performance.trades_closed + 1) > 0 
                        THEN ((monitoring.daily_performance.winning_trades + CASE WHEN is_winning_trade THEN 1 ELSE 0 END) * 100.0) / (monitoring.daily_performance.trades_closed + 1)
                        ELSE 0 
                    END;
            END IF;
            
            RETURN NEW;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    # trades 테이블에 트리거 적용
    op.execute("""
        CREATE TRIGGER trigger_update_daily_performance
            AFTER INSERT ON trading.trades
            FOR EACH ROW
            EXECUTE FUNCTION monitoring.update_daily_performance_on_trade();
    """)
    
    # 페어별 성과 자동 업데이트 함수
    op.execute("""
        CREATE OR REPLACE FUNCTION monitoring.update_pair_performance_on_trade()
        RETURNS TRIGGER AS $
        DECLARE
            trade_date DATE := DATE(NEW.execution_time);
            is_winning_trade BOOLEAN := (NEW.net_pnl_usd > 0);
        BEGIN
            IF NEW.trade_type = 'CLOSE' THEN
                INSERT INTO monitoring.pair_performance (
                    date,
                    pair_id,
                    pnl_usd,
                    trades_count,
                    win_rate
                ) VALUES (
                    trade_date,
                    NEW.pair_id,
                    COALESCE(NEW.net_pnl_usd, 0),
                    1,
                    CASE WHEN is_winning_trade THEN 100.0 ELSE 0.0 END
                )
                ON CONFLICT (date, pair_id) DO UPDATE SET
                    pnl_usd = monitoring.pair_performance.pnl_usd + COALESCE(NEW.net_pnl_usd, 0),
                    trades_count = monitoring.pair_performance.trades_count + 1,
                    win_rate = CASE 
                        WHEN (monitoring.pair_performance.trades_count + 1) > 0 
                        THEN (
                            (CASE WHEN monitoring.pair_performance.win_rate * monitoring.pair_performance.trades_count / 100.0 + CASE WHEN is_winning_trade THEN 1 ELSE 0 END END) * 100.0
                        ) / (monitoring.pair_performance.trades_count + 1)
                        ELSE 0 
                    END;
            END IF;
            
            RETURN NEW;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_update_pair_performance
            AFTER INSERT ON trading.trades
            FOR EACH ROW
            EXECUTE FUNCTION monitoring.update_pair_performance_on_trade();
    """)
    
    # 시스템 헬스 알림 트리거 함수
    op.execute("""
        CREATE OR REPLACE FUNCTION monitoring.notify_system_health_issues()
        RETURNS TRIGGER AS $
        BEGIN
            -- CRITICAL 상태나 높은 에러율 시 알림
            IF (NEW.data_collection_status = 'ERROR' OR 
                NEW.analysis_engine_status = 'ERROR' OR 
                NEW.execution_engine_status = 'ERROR' OR
                NEW.kalman_filter_errors_count > 10 OR
                NEW.exchange_api_errors_count > 20) THEN
                
                PERFORM pg_notify(
                    'system_health_alert',
                    json_build_object(
                        'time', NEW.time,
                        'data_status', NEW.data_collection_status,
                        'analysis_status', NEW.analysis_engine_status,
                        'execution_status', NEW.execution_engine_status,
                        'kalman_errors', NEW.kalman_filter_errors_count,
                        'api_errors', NEW.exchange_api_errors_count
                    )::text
                );
            END IF;
            
            RETURN NEW;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_notify_system_health_issues
            AFTER INSERT ON monitoring.system_health
            FOR EACH ROW
            EXECUTE FUNCTION monitoring.notify_system_health_issues();
    """)
    
    print("✅ 자동 집계 트리거 함수 생성 완료")
    
    # =================================================================
    # 8. 초기 권한 설정
    # =================================================================
    
    print("🔐 모니터링 테이블 권한 설정 중...")
    
    # 애플리케이션 사용자 권한
    for table in ['daily_performance', 'pair_performance', 'system_health', 'error_logs']:
        op.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON monitoring.{table} TO odysseus_app;
        """)
    
    # 읽기 전용 사용자 권한 (대시보드용)
    for table in ['daily_performance', 'pair_performance', 'system_health', 'error_logs']:
        op.execute(f"""
            GRANT SELECT ON monitoring.{table} TO odysseus_readonly;
        """)
    
    print("✅ 권한 설정 완료")
    
    # =================================================================
    # 9. 샘플 데이터 및 초기 설정
    # =================================================================
    
    print("📝 모니터링 테이블 초기 데이터 설정 중...")
    
    # 오늘의 기본 성과 레코드
    op.execute("""
        INSERT INTO monitoring.daily_performance (date)
        VALUES (CURRENT_DATE)
        ON CONFLICT (date) DO NOTHING;
    """)
    
    # 초기 시스템 헬스 레코드
    op.execute("""
        INSERT INTO monitoring.system_health (
            time,
            data_collection_status,
            analysis_engine_status,
            execution_engine_status,
            cpu_usage_pct,
            memory_usage_pct,
            disk_usage_pct
        ) VALUES (
            NOW(),
            'HEALTHY',
            'HEALTHY',
            'HEALTHY',
            0.0,
            0.0,
            0.0
        );
    """)
    
    print("✅ 모니터링 테이블 생성 완료!")

def downgrade() -> None:
    """모니터링 테이블 제거"""
    
    print("🗑️ 모니터링 테이블 제거 중...")
    
    # =================================================================
    # 1. 트리거 및 함수 제거
    # =================================================================
    
    print("⚡ 트리거 및 함수 제거 중...")
    
    # 트리거 제거
    op.execute("DROP TRIGGER IF EXISTS trigger_update_daily_performance ON trading.trades;")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_pair_performance ON trading.trades;")
    op.execute("DROP TRIGGER IF EXISTS trigger_notify_system_health_issues ON monitoring.system_health;")
    
    # 함수 제거
    op.execute("DROP FUNCTION IF EXISTS monitoring.update_daily_performance_on_trade();")
    op.execute("DROP FUNCTION IF EXISTS monitoring.update_pair_performance_on_trade();")
    op.execute("DROP FUNCTION IF EXISTS monitoring.notify_system_health_issues();")
    
    # =================================================================
    # 2. 압축 정책 제거
    # =================================================================
    
    print("🗜️ 압축 정책 제거 중...")
    
    op.execute("""
        SELECT remove_compression_policy('monitoring.system_health', if_not_exists => true);
    """)
    
    op.execute("""
        SELECT remove_compression_policy('monitoring.error_logs', if_not_exists => true);
    """)
    
    # =================================================================
    # 3. 외래키 제약 조건 제거
    # =================================================================
    
    print("🔗 외래키 제약 조건 제거 중...")
    
    # error_logs 외래키들
    op.drop_constraint('fk_error_logs_pair_id', 'error_logs',
                      schema='monitoring', type_='foreignkey')
    op.drop_constraint('fk_error_logs_trade_id', 'error_logs',
                      schema='monitoring', type_='foreignkey')
    op.drop_constraint('fk_error_logs_position_id', 'error_logs',
                      schema='monitoring', type_='foreignkey')
    
    # pair_performance 외래키
    op.drop_constraint('fk_pair_performance_pair_id', 'pair_performance',
                      schema='monitoring', type_='foreignkey')
    
    # =================================================================
    # 4. 테이블 제거
    # =================================================================
    
    print("📊 모니터링 테이블 제거 중...")
    
    # 의존성 순서대로 제거
    tables_to_drop = [
        'error_logs',        # 외래키 의존성 있음
        'system_health',     # 하이퍼테이블
        'pair_performance',  # 외래키 의존성 있음
        'daily_performance'  # 기본 테이블
    ]
    
    for table in tables_to_drop:
        op.drop_table(table, schema='monitoring')
        print(f"✅ {table} 테이블 제거 완료")
    
    print("✅ 모니터링 테이블 롤백 완료")