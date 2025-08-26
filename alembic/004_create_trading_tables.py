"""Create trading execution tables

Revision ID: 004_trading_tables
Revises: 003_analysis_tables  
Create Date: 2024-01-01 00:03:00.000000

거래 실행 및 포지션 관리를 위한 테이블들을 생성합니다:
- positions: 현재 열린 포지션들
- trades: 완료된 거래 기록 
- order_executions: 개별 주문 실행 로그

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_trading_tables'
down_revision = '003_analysis_tables'
branch_labels = None
depends_on = None

def get_env_policies():
    """환경별 정책 가져오기"""
    from alembic import context
    return getattr(context, '_env_policies', {
        'compression_after': 'INTERVAL \'7 days\'',
    })

def upgrade() -> None:
    """거래 실행 테이블 생성"""
    
    print("💰 거래 실행 테이블 생성 중...")
    
    # =================================================================
    # 1. positions 테이블 생성 (현재 열린 포지션들)
    # =================================================================
    
    print("📍 positions 테이블 생성 중...")
    
    op.create_table(
        'positions',
        # Primary Key
        sa.Column('position_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='포지션 고유 ID'),
        
        # 페어 및 신호 참조
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        sa.Column('entry_signal_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='진입 신호 ID'),
        
        # 포지션 기본 정보
        sa.Column('side', sa.String(5), nullable=False,
                  comment='포지션 방향 (LONG/SHORT)'),
        
        # 진입 정보
        sa.Column('entry_time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='포지션 진입 시간'),
        sa.Column('entry_z_score', sa.Numeric(8, 4), nullable=False,
                  comment='진입 시점 Z-score'),
        sa.Column('entry_hedge_ratio', sa.Numeric(12, 6), nullable=False,
                  comment='진입 시점 헤지 비율'),
        
        # 포지션 크기 (USD 기준)
        sa.Column('position_size_usd', sa.Numeric(15, 2), nullable=False,
                  comment='포지션 크기 (USD)'),
        sa.Column('symbol_a_quantity', sa.Numeric(20, 8), nullable=True,
                  comment='첫 번째 자산 수량'),
        sa.Column('symbol_b_quantity', sa.Numeric(20, 8), nullable=True,
                  comment='두 번째 자산 수량'),
        sa.Column('symbol_a_entry_price', sa.Numeric(20, 8), nullable=True,
                  comment='첫 번째 자산 진입 가격'),
        sa.Column('symbol_b_entry_price', sa.Numeric(20, 8), nullable=True,
                  comment='두 번째 자산 진입 가격'),
        
        # 현재 상태 (실시간 업데이트)
        sa.Column('current_z_score', sa.Numeric(8, 4), nullable=True,
                  comment='현재 Z-score'),
        sa.Column('current_pnl_usd', sa.Numeric(15, 4), nullable=True,
                  comment='현재 손익 (USD)'),
        sa.Column('current_pnl_pct', sa.Numeric(8, 4), nullable=True,
                  comment='현재 손익률'),
        
        # 리스크 관리 설정
        sa.Column('stop_loss_z_score', sa.Numeric(5, 2), nullable=True,
                  comment='손절 Z-score 임계값'),
        sa.Column('max_holding_days', sa.Integer, nullable=False, server_default='10',
                  comment='최대 보유 일수'),
        
        # 포지션 상태
        sa.Column('status', sa.String(10), nullable=False, server_default='OPEN',
                  comment='포지션 상태'),
        
        # 시간 추적
        sa.Column('last_updated', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()'),
                  comment='마지막 업데이트 시간'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('position_id'),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name='valid_position_side'),
        sa.CheckConstraint('position_size_usd > 0', name='positive_position_size'),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSING', 'CLOSED')", name='valid_position_status'),
        sa.CheckConstraint('max_holding_days > 0', name='positive_holding_days'),
        sa.CheckConstraint('stop_loss_z_score > 0', name='positive_stop_loss'),
        
        schema='trading',
        comment='현재 열린 포지션 정보'
    )
    
    # 외래키 제약 조건들
    op.create_foreign_key(
        'fk_positions_pair_id',
        'positions', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='trading', referent_schema='analysis'
    )
    
    op.create_foreign_key(
        'fk_positions_entry_signal_id',
        'positions', 'signals',
        ['entry_signal_id'], ['signal_id'],
        source_schema='trading', referent_schema='analysis'
    )
    
    # =================================================================
    # 2. trades 테이블 생성 (완료된 거래들)
    # =================================================================
    
    print("📈 trades 테이블 생성 중...")
    
    op.create_table(
        'trades',
        # Primary Key
        sa.Column('trade_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='거래 고유 ID'),
        
        # 포지션 및 페어 참조
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='관련 포지션 ID'),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        
        # 거래 기본 정보
        sa.Column('trade_type', sa.String(10), nullable=False,
                  comment='거래 타입 (OPEN/CLOSE/REBALANCE)'),
        sa.Column('side', sa.String(5), nullable=False,
                  comment='거래 방향 (LONG/SHORT)'),
        
        # 거래 시간 정보
        sa.Column('signal_time', postgresql.TIMESTAMP(timezone=True), nullable=True,
                  comment='신호 발생 시간'),
        sa.Column('execution_time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='실제 실행 시간'),
        sa.Column('execution_delay_seconds', sa.Integer, nullable=True,
                  comment='신호-실행 지연시간(초)'),
        
        # 진입/청산 정보
        sa.Column('entry_z_score', sa.Numeric(8, 4), nullable=True,
                  comment='진입 Z-score'),
        sa.Column('exit_z_score', sa.Numeric(8, 4), nullable=True,
                  comment='청산 Z-score'),
        sa.Column('hedge_ratio', sa.Numeric(12, 6), nullable=False,
                  comment='거래 시점 헤지 비율'),
        
        # 거래 수량 및 가격
        sa.Column('symbol_a_quantity', sa.Numeric(20, 8), nullable=False,
                  comment='첫 번째 자산 거래 수량'),
        sa.Column('symbol_b_quantity', sa.Numeric(20, 8), nullable=False,
                  comment='두 번째 자산 거래 수량'),
        sa.Column('symbol_a_price', sa.Numeric(20, 8), nullable=False,
                  comment='첫 번째 자산 거래 가격'),
        sa.Column('symbol_b_price', sa.Numeric(20, 8), nullable=False,
                  comment='두 번째 자산 거래 가격'),
        
        # 손익 정보
        sa.Column('gross_pnl_usd', sa.Numeric(15, 4), nullable=True,
                  comment='총 손익 (수수료 제외)'),
        sa.Column('fees_usd', sa.Numeric(10, 4), nullable=True,
                  comment='거래 수수료'),
        sa.Column('net_pnl_usd', sa.Numeric(15, 4), nullable=True,
                  comment='순 손익 (수수료 포함)'),
        sa.Column('pnl_pct', sa.Numeric(8, 4), nullable=True,
                  comment='손익률'),
        
        # 실행 품질 메트릭
        sa.Column('expected_slippage_bps', sa.Integer, nullable=True,
                  comment='예상 슬리피지 (bps)'),
        sa.Column('actual_slippage_bps', sa.Integer, nullable=True,
                  comment='실제 슬리피지 (bps)'),
        sa.Column('execution_quality', sa.String(10), nullable=True,
                  comment='실행 품질 평가'),
        
        # 거래 종료 사유
        sa.Column('close_reason', sa.String(20), nullable=True,
                  comment='포지션 종료 사유'),
        
        # 메타데이터
        sa.Column('executed_by', sa.String(50), nullable=False, server_default='execution_handler',
                  comment='실행 모듈'),
        sa.Column('notes', sa.Text, nullable=True,
                  comment='추가 설명'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('trade_id'),
        sa.CheckConstraint("trade_type IN ('OPEN', 'CLOSE', 'REBALANCE')", name='valid_trade_type'),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name='valid_trade_side'),
        sa.CheckConstraint('symbol_a_quantity != 0 AND symbol_b_quantity != 0', name='non_zero_quantities'),
        sa.CheckConstraint('symbol_a_price > 0 AND symbol_b_price > 0', name='positive_prices'),
        sa.CheckConstraint("execution_quality IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR') OR execution_quality IS NULL", 
                          name='valid_execution_quality'),
        sa.CheckConstraint("close_reason IN ('SIGNAL', 'STOP_LOSS', 'TIME_LIMIT', 'MANUAL', 'RISK_MGMT') OR close_reason IS NULL", 
                          name='valid_close_reason'),
        sa.CheckConstraint('execution_delay_seconds >= 0', name='non_negative_delay'),
        
        schema='trading',
        comment='완료된 거래 기록'
    )
    
    # 외래키 제약 조건들
    op.create_foreign_key(
        'fk_trades_position_id',
        'trades', 'positions',
        ['position_id'], ['position_id'],
        source_schema='trading', referent_schema='trading'
    )
    
    op.create_foreign_key(
        'fk_trades_pair_id',
        'trades', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='trading', referent_schema='analysis'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 trades를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'trading.trades', 
            'execution_time',
            chunk_time_interval => INTERVAL '1 month'
        );
    """)
    
    # =================================================================
    # 3. order_executions 테이블 생성 (상세 주문 로그)
    # =================================================================
    
    print("📋 order_executions 테이블 생성 중...")
    
    op.create_table(
        'order_executions',
        # Primary Key
        sa.Column('execution_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='주문 실행 고유 ID'),
        
        # 거래 참조
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='관련 거래 ID'),
        
        # 주문 정보
        sa.Column('symbol', sa.String(20), nullable=False,
                  comment='거래 심볼'),
        sa.Column('side', sa.String(4), nullable=False,
                  comment='주문 방향 (buy/sell)'),
        sa.Column('order_type', sa.String(10), nullable=False,
                  comment='주문 타입 (limit/market/twap)'),
        
        # 주문 수량 및 가격
        sa.Column('requested_quantity', sa.Numeric(20, 8), nullable=False,
                  comment='요청 수량'),
        sa.Column('requested_price', sa.Numeric(20, 8), nullable=True,
                  comment='요청 가격 (limit 주문)'),
        
        # 체결 결과
        sa.Column('filled_quantity', sa.Numeric(20, 8), nullable=True,
                  comment='체결된 수량'),
        sa.Column('average_fill_price', sa.Numeric(20, 8), nullable=True,
                  comment='평균 체결 가격'),
        sa.Column('total_fee', sa.Numeric(12, 6), nullable=True,
                  comment='총 수수료'),
        sa.Column('fee_asset', sa.String(10), nullable=True,
                  comment='수수료 자산'),
        
        # 실행 상태 및 시간
        sa.Column('order_status', sa.String(15), nullable=False,
                  comment='주문 상태'),
        sa.Column('submitted_at', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='주문 제출 시간'),
        sa.Column('filled_at', postgresql.TIMESTAMP(timezone=True), nullable=True,
                  comment='체결 완료 시간'),
        
        # 거래소 정보
        sa.Column('exchange_order_id', sa.String(50), nullable=True,
                  comment='거래소 주문 ID'),
        sa.Column('exchange', sa.String(20), nullable=False, server_default='binance',
                  comment='거래소'),
        
        # 에러 정보
        sa.Column('error_code', sa.String(20), nullable=True,
                  comment='에러 코드'),
        sa.Column('error_message', sa.Text, nullable=True,
                  comment='에러 메시지'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('execution_id'),
        sa.CheckConstraint("side IN ('buy', 'sell')", name='valid_order_side'),
        sa.CheckConstraint("order_type IN ('limit', 'market', 'twap')", name='valid_order_type'),
        sa.CheckConstraint('requested_quantity > 0', name='positive_requested_quantity'),
        sa.CheckConstraint('requested_price > 0 OR requested_price IS NULL', name='positive_requested_price'),
        sa.CheckConstraint('filled_quantity >= 0 OR filled_quantity IS NULL', name='non_negative_filled_quantity'),
        sa.CheckConstraint('average_fill_price > 0 OR average_fill_price IS NULL', name='positive_fill_price'),
        sa.CheckConstraint("order_status IN ('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED')", 
                          name='valid_order_status'),
        
        schema='trading',
        comment='개별 주문 실행 상세 로그'
    )
    
    # 외래키 제약 조건
    op.create_foreign_key(
        'fk_order_executions_trade_id',
        'order_executions', 'trades',
        ['trade_id'], ['trade_id'],
        source_schema='trading', referent_schema='trading'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 order_executions를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'trading.order_executions', 
            'submitted_at',
            chunk_time_interval => INTERVAL '1 week'
        );
    """)
    
    # =================================================================
    # 4. 인덱스 생성 (성능 최적화)
    # =================================================================
    
    print("🔍 거래 테이블 인덱스 생성 중...")
    
    # positions 테이블 인덱스 (실시간 조회 최적화)
    op.execute("""
        CREATE INDEX idx_positions_status_time 
        ON trading.positions (status, entry_time DESC) 
        WHERE status = 'OPEN';
    """)
    
    op.execute("""
        CREATE INDEX idx_positions_pair_status 
        ON trading.positions (pair_id, status);
    """)
    
    op.execute("""
        CREATE INDEX idx_positions_z_score_risk 
        ON trading.positions (current_z_score, stop_loss_z_score) 
        WHERE status = 'OPEN' AND current_z_score IS NOT NULL;
    """)
    
    # trades 테이블 인덱스 (성과 분석 최적화)
    op.execute("""
        CREATE INDEX idx_trades_execution_time 
        ON trading.trades (execution_time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_trades_pair_performance 
        ON trading.trades (pair_id, execution_time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_trades_pnl_analysis 
        ON trading.trades (execution_time DESC, net_pnl_usd DESC)
        WHERE trade_type = 'CLOSE';
    """)
    
    op.execute("""
        CREATE INDEX idx_trades_type_side 
        ON trading.trades (trade_type, side, execution_time DESC);
    """)
    
    # order_executions 테이블 인덱스 (실행 품질 분석)
    op.execute("""
        CREATE INDEX idx_order_executions_status_time 
        ON trading.order_executions (order_status, submitted_at DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_order_executions_symbol_time 
        ON trading.order_executions (symbol, submitted_at DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_order_executions_exchange_order_id 
        ON trading.order_executions (exchange, exchange_order_id)
        WHERE exchange_order_id IS NOT NULL;
    """)
    
    # =================================================================
    # 5. 압축 정책 적용
    # =================================================================
    
    print("🗜️ 거래 테이블 압축 정책 적용 중...")
    
    policies = get_env_policies()
    compression_after = policies.get('compression_after', 'INTERVAL \'7 days\'')
    
    # trades 테이블 압축 (중요한 데이터이므로 보수적)
    op.execute(f"""
        SELECT add_compression_policy(
            'trading.trades', 
            {compression_after}
        );
    """)
    
    # order_executions 테이블 압축 (더 빠른 압축)
    op.execute(f"""
        SELECT add_compression_policy(
            'trading.order_executions', 
            INTERVAL '3 days'
        );
    """)
    
    print("✅ 압축 정책 적용 완료")
    
    # =================================================================
    # 6. 트리거 함수 생성 (자동 업데이트)
    # =================================================================
    
    print("⚡ 트리거 함수 생성 중...")
    
    # 포지션 PnL 자동 계산 트리거 함수
    op.execute("""
        CREATE OR REPLACE FUNCTION trading.calculate_position_pnl()
        RETURNS TRIGGER AS $
        DECLARE
            symbol_a_current_price DECIMAL(20,8);
            symbol_b_current_price DECIMAL(20,8);
            current_spread DECIMAL(20,8);
            entry_spread DECIMAL(20,8);
            pnl_usd DECIMAL(15,4);
            pnl_pct DECIMAL(8,4);
        BEGIN
            -- 최신 가격 정보 조회
            SELECT pd_a.close, pd_b.close 
            INTO symbol_a_current_price, symbol_b_current_price
            FROM analysis.trading_pairs tp
            JOIN market_data.price_data pd_a ON pd_a.symbol = tp.symbol_a
            JOIN market_data.price_data pd_b ON pd_b.symbol = tp.symbol_b
            WHERE tp.pair_id = NEW.pair_id
              AND pd_a.timeframe = '1h'
              AND pd_b.timeframe = '1h'
              AND pd_a.time = pd_b.time
            ORDER BY pd_a.time DESC
            LIMIT 1;
            
            -- PnL 계산
            IF symbol_a_current_price IS NOT NULL AND symbol_b_current_price IS NOT NULL THEN
                entry_spread := OLD.symbol_a_entry_price - (OLD.entry_hedge_ratio * OLD.symbol_b_entry_price);
                current_spread := symbol_a_current_price - (NEW.entry_hedge_ratio * symbol_b_current_price);
                
                IF NEW.side = 'LONG' THEN
                    pnl_usd := (current_spread - entry_spread) * NEW.symbol_a_quantity;
                ELSE
                    pnl_usd := (entry_spread - current_spread) * NEW.symbol_a_quantity;
                END IF;
                
                pnl_pct := pnl_usd / NEW.position_size_usd;
                
                NEW.current_pnl_usd := pnl_usd;
                NEW.current_pnl_pct := pnl_pct;
                NEW.last_updated := NOW();
            END IF;
            
            RETURN NEW;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    # positions 테이블에 트리거 생성
    op.execute("""
        CREATE TRIGGER trigger_calculate_position_pnl
            BEFORE UPDATE ON trading.positions
            FOR EACH ROW
            EXECUTE FUNCTION trading.calculate_position_pnl();
    """)
    
    # 거래 완료 시 포지션 상태 업데이트 트리거
    op.execute("""
        CREATE OR REPLACE FUNCTION trading.update_position_on_trade()
        RETURNS TRIGGER AS $
        BEGIN
            -- CLOSE 거래 시 포지션 상태를 CLOSED로 변경
            IF NEW.trade_type = 'CLOSE' AND NEW.position_id IS NOT NULL THEN
                UPDATE trading.positions 
                SET status = 'CLOSED', 
                    last_updated = NEW.execution_time
                WHERE position_id = NEW.position_id;
            END IF;
            
            RETURN NEW;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_update_position_on_trade
            AFTER INSERT ON trading.trades
            FOR EACH ROW
            EXECUTE FUNCTION trading.update_position_on_trade();
    """)
    
    print("✅ 트리거 함수 생성 완료")
    
    # =================================================================
    # 7. 초기 권한 설정
    # =================================================================
    
    print("🔐 테이블 권한 설정 중...")
    
    # 애플리케이션 사용자에게 모든 권한
    for table in ['positions', 'trades', 'order_executions']:
        op.execute(f"""
            GRANT SELECT, INSERT, UPDATE, DELETE ON trading.{table} TO odysseus_app;
        """)
    
    # 읽기 전용 사용자에게 SELECT 권한만
    for table in ['positions', 'trades', 'order_executions']:
        op.execute(f"""
            GRANT SELECT ON trading.{table} TO odysseus_readonly;
        """)
    
    print("✅ 권한 설정 완료")
    
    # =================================================================
    # 8. 샘플 데이터 삽입 (테스트용)
    # =================================================================
    
    print("📝 거래 테이블 샘플 데이터 삽입 중...")
    
    # 샘플 포지션 (테스트용 - 실제 운영에서는 제거)
    op.execute("""
        DO $
        DECLARE
            sample_pair_id UUID;
        BEGIN
            -- 첫 번째 페어 ID 조회
            SELECT pair_id INTO sample_pair_id 
            FROM analysis.trading_pairs 
            WHERE is_active = TRUE 
            LIMIT 1;
            
            IF sample_pair_id IS NOT NULL THEN
                -- 샘플 포지션 삽입
                INSERT INTO trading.positions 
                (pair_id, side, entry_time, entry_z_score, entry_hedge_ratio, 
                 position_size_usd, symbol_a_quantity, symbol_b_quantity,
                 symbol_a_entry_price, symbol_b_entry_price, status)
                VALUES 
                (sample_pair_id, 'LONG', NOW() - INTERVAL '2 hours', 2.1, 0.85,
                 1000.00, 0.02, 0.5, 50000, 3200, 'OPEN')
                ON CONFLICT DO NOTHING;
                
                RAISE NOTICE 'Sample position inserted for pair_id: %', sample_pair_id;
            END IF;
        END $;
    """)
    
    print("✅ 거래 테이블 생성 완료!")

def downgrade() -> None:
    """거래 테이블 제거"""
    
    print("🗑️ 거래 테이블 제거 중...")
    
    # =================================================================
    # 1. 트리거 및 함수 제거
    # =================================================================
    
    print("⚡ 트리거 및 함수 제거 중...")
    
    # 트리거 제거
    op.execute("DROP TRIGGER IF EXISTS trigger_calculate_position_pnl ON trading.positions;")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_position_on_trade ON trading.trades;")
    
    # 함수 제거
    op.execute("DROP FUNCTION IF EXISTS trading.calculate_position_pnl();")
    op.execute("DROP FUNCTION IF EXISTS trading.update_position_on_trade();")
    
    # =================================================================
    # 2. 압축 정책 제거
    # =================================================================
    
    print("🗜️ 압축 정책 제거 중...")
    
    op.execute("""
        SELECT remove_compression_policy('trading.trades', if_not_exists => true);
    """)
    
    op.execute("""
        SELECT remove_compression_policy('trading.order_executions', if_not_exists => true);
    """)
    
    # =================================================================
    # 3. 외래키 제약 조건 제거
    # =================================================================
    
    print("🔗 외래키 제약 조건 제거 중...")
    
    # order_executions 외래키
    op.drop_constraint('fk_order_executions_trade_id', 'order_executions', 
                      schema='trading', type_='foreignkey')
    
    # trades 외래키들
    op.drop_constraint('fk_trades_position_id', 'trades', 
                      schema='trading', type_='foreignkey')
    op.drop_constraint('fk_trades_pair_id', 'trades', 
                      schema='trading', type_='foreignkey')
    
    # positions 외래키들
    op.drop_constraint('fk_positions_pair_id', 'positions', 
                      schema='trading', type_='foreignkey')
    op.drop_constraint('fk_positions_entry_signal_id', 'positions', 
                      schema='trading', type_='foreignkey')
    
    # =================================================================
    # 4. 테이블 제거 (의존성 역순)
    # =================================================================
    
    print("📊 거래 테이블 제거 중...")
    
    # 의존성 순서대로 제거
    tables_to_drop = [
        'order_executions',  # 가장 하위 의존성
        'trades',           # 중간 의존성
        'positions'         # 기본 테이블
    ]
    
    for table in tables_to_drop:
        op.drop_table(table, schema='trading')
        print(f"✅ {table} 테이블 제거 완료")
    
    print("✅ 거래 테이블 롤백 완료")