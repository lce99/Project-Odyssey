"""Create market data tables

Revision ID: 002_market_data_tables
Revises: 001_schemas_extensions
Create Date: 2024-01-01 00:01:00.000000

시장 데이터 수집을 위한 핵심 테이블들을 생성합니다:
- price_data: OHLCV 가격 데이터 (TimescaleDB 하이퍼테이블)
- orderbook_data: 실시간 오더북 데이터
- trade_ticks: 개별 거래 데이터 (확장성 고려)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_market_data_tables'
down_revision = '001_schemas_extensions'
branch_labels = None
depends_on = None

def get_env_policies():
    """환경별 정책 가져오기"""
    from alembic import context
    return getattr(context, '_env_policies', {
        'compression_after': 'INTERVAL \'7 days\'',
        'price_data_retention': 'INTERVAL \'6 months\'',
        'orderbook_retention': 'INTERVAL \'1 month\'',
        'analysis_retention': 'INTERVAL \'1 year\'',
    })

def upgrade() -> None:
    """시장 데이터 테이블 생성"""
    
    print("📊 시장 데이터 테이블 생성 중...")
    
    # =================================================================
    # 1. price_data 테이블 생성 (핵심 OHLCV 데이터)
    # =================================================================
    
    print("💹 price_data 테이블 생성 중...")
    
    op.create_table(
        'price_data',
        # 시간 컬럼 (파티셔닝 키)
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='캔들스틱 시간 (UTC)'),
        
        # 심볼 및 메타데이터
        sa.Column('symbol', sa.String(20), nullable=False,
                  comment='거래 심볼 (예: BTC/USDT)'),
        sa.Column('exchange', sa.String(20), nullable=False, server_default='binance',
                  comment='거래소 이름'),
        sa.Column('timeframe', sa.String(10), nullable=False,
                  comment='시간봉 (1m, 1h, 1d)'),
        
        # OHLCV 가격 데이터
        sa.Column('open', sa.Numeric(20, 8), nullable=False,
                  comment='시가'),
        sa.Column('high', sa.Numeric(20, 8), nullable=False,
                  comment='고가'),
        sa.Column('low', sa.Numeric(20, 8), nullable=False,
                  comment='저가'),
        sa.Column('close', sa.Numeric(20, 8), nullable=False,
                  comment='종가'),
        sa.Column('volume', sa.Numeric(20, 8), nullable=False,
                  comment='거래량 (Base Asset)'),
        
        # 추가 거래 정보
        sa.Column('quote_volume', sa.Numeric(20, 8), nullable=True,
                  comment='Quote Asset 거래량'),
        sa.Column('trades_count', sa.Integer, nullable=True,
                  comment='거래 횟수'),
        sa.Column('taker_buy_volume', sa.Numeric(20, 8), nullable=True,
                  comment='Taker buy 거래량'),
        sa.Column('taker_buy_quote_volume', sa.Numeric(20, 8), nullable=True,
                  comment='Taker buy quote 거래량'),
        
        # 데이터 품질 관리
        sa.Column('is_interpolated', sa.Boolean, nullable=False, server_default='false',
                  comment='보간된 데이터 여부'),
        sa.Column('data_source', sa.String(50), nullable=False, server_default='api',
                  comment='데이터 소스 (api, websocket, manual)'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), 
                  nullable=False, server_default=sa.text('NOW()'),
                  comment='레코드 생성 시간'),
        
        # 제약 조건
        sa.CheckConstraint('open > 0 AND high > 0 AND low > 0 AND close > 0', 
                          name='price_data_positive_prices'),
        sa.CheckConstraint('high >= open AND high >= close AND low <= open AND low <= close', 
                          name='price_data_ohlc_logic'),
        sa.CheckConstraint('volume >= 0', name='price_data_positive_volume'),
        sa.CheckConstraint("data_source IN ('api', 'websocket', 'manual')", 
                          name='price_data_valid_source'),
        
        schema='market_data',
        comment='OHLCV 가격 데이터 - TimescaleDB 하이퍼테이블'
    )
    
    # TimescaleDB 하이퍼테이블 생성
    print("🕐 price_data를 TimescaleDB 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'market_data.price_data', 
            'time',
            chunk_time_interval => INTERVAL '1 day',
            create_default_indexes => FALSE
        );
    """)
    
    # =================================================================
    # 2. orderbook_data 테이블 생성 (실시간 유동성 정보)
    # =================================================================
    
    print("📖 orderbook_data 테이블 생성 중...")
    
    op.create_table(
        'orderbook_data',
        # 시간 및 기본 정보
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='오더북 스냅샷 시간'),
        sa.Column('symbol', sa.String(20), nullable=False,
                  comment='거래 심볼'),
        sa.Column('exchange', sa.String(20), nullable=False, server_default='binance',
                  comment='거래소 이름'),
        
        # 매수/매도 구분 및 레벨
        sa.Column('side', sa.String(4), nullable=False,
                  comment='주문 방향 (bid/ask)'),
        sa.Column('level', sa.Integer, nullable=False,
                  comment='오더북 레벨 (1-10)'),
        
        # 가격 및 수량
        sa.Column('price', sa.Numeric(20, 8), nullable=False,
                  comment='해당 레벨의 가격'),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False,
                  comment='해당 레벨의 수량'),
        
        # 메타데이터
        sa.Column('last_update_id', sa.BigInteger, nullable=True,
                  comment='거래소의 마지막 업데이트 ID'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.CheckConstraint("side IN ('bid', 'ask')", name='orderbook_valid_side'),
        sa.CheckConstraint('level BETWEEN 1 AND 10', name='orderbook_valid_level'),
        sa.CheckConstraint('price > 0', name='orderbook_positive_price'),
        sa.CheckConstraint('quantity > 0', name='orderbook_positive_quantity'),
        
        schema='market_data',
        comment='실시간 오더북 데이터 - 최대 10레벨까지 저장'
    )
    
    # TimescaleDB 하이퍼테이블 생성 (더 짧은 청크)
    print("🕐 orderbook_data를 TimescaleDB 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'market_data.orderbook_data', 
            'time',
            chunk_time_interval => INTERVAL '6 hours'
        );
    """)
    
    # =================================================================
    # 3. trade_ticks 테이블 생성 (확장 가능성 고려)
    # =================================================================
    
    print("🎯 trade_ticks 테이블 생성 중...")
    
    op.create_table(
        'trade_ticks',
        # 시간 및 기본 정보
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='거래 실행 시간'),
        sa.Column('symbol', sa.String(20), nullable=False,
                  comment='거래 심볼'),
        sa.Column('exchange', sa.String(20), nullable=False, server_default='binance',
                  comment='거래소 이름'),
        
        # 거래 정보
        sa.Column('trade_id', sa.BigInteger, nullable=False,
                  comment='거래소 거래 ID'),
        sa.Column('price', sa.Numeric(20, 8), nullable=False,
                  comment='거래 가격'),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False,
                  comment='거래 수량'),
        sa.Column('side', sa.String(4), nullable=False,
                  comment='거래 방향 (buy/sell)'),
        
        # 추가 정보
        sa.Column('is_buyer_maker', sa.Boolean, nullable=True,
                  comment='매수자가 Maker인지 여부'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.CheckConstraint('price > 0', name='trade_ticks_positive_price'),
        sa.CheckConstraint('quantity > 0', name='trade_ticks_positive_quantity'),
        sa.CheckConstraint("side IN ('buy', 'sell')", name='trade_ticks_valid_side'),
        
        schema='market_data',
        comment='개별 거래 틱 데이터 - 향후 확장성 고려'
    )
    
    print("ℹ️ trade_ticks는 초기에 비활성화 상태 (필요시 하이퍼테이블 변환)")
    
    # =================================================================
    # 4. 기본 인덱스 생성 (성능 최적화)
    # =================================================================
    
    print("🔍 기본 인덱스 생성 중...")
    
    # price_data 핵심 인덱스들
    op.execute("""
        CREATE INDEX idx_price_data_symbol_time 
        ON market_data.price_data (symbol, time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_price_data_symbol_timeframe_time 
        ON market_data.price_data (symbol, timeframe, time DESC);
    """)
    
    # 복합 페어 조회용 (중요한 timeframe만)
    op.execute("""
        CREATE INDEX idx_price_data_multi_symbol_time 
        ON market_data.price_data (time DESC, symbol) 
        WHERE timeframe = '1h';
    """)
    
    # orderbook_data 인덱스
    op.execute("""
        CREATE INDEX idx_orderbook_symbol_time_side 
        ON market_data.orderbook_data (symbol, time DESC, side, level);
    """)
    
    # trade_ticks 인덱스 (향후 사용 대비)
    op.execute("""
        CREATE INDEX idx_trade_ticks_symbol_time 
        ON market_data.trade_ticks (symbol, time DESC);
    """)
    
    # =================================================================
    # 5. 압축 정책 적용
    # =================================================================
    
    print("🗜️ 압축 정책 적용 중...")
    
    policies = get_env_policies()
    compression_after = policies.get('compression_after', 'INTERVAL \'7 days\'')
    
    # price_data 압축 정책
    op.execute(f"""
        SELECT add_compression_policy(
            'market_data.price_data', 
            {compression_after}
        );
    """)
    
    # orderbook_data 압축 정책 (더 빠른 압축)
    op.execute(f"""
        SELECT add_compression_policy(
            'market_data.orderbook_data', 
            INTERVAL '1 day'
        );
    """)
    
    print("✅ 압축 정책 적용 완료")
    
    # =================================================================
    # 6. 샘플 데이터 삽입 (테스트용)
    # =================================================================
    
    print("📝 샘플 데이터 삽입 중...")
    
    # 기본적인 심볼들의 샘플 데이터
    sample_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    
    for symbol in sample_symbols:
        op.execute(f"""
            INSERT INTO market_data.price_data 
            (time, symbol, timeframe, open, high, low, close, volume, data_source)
            VALUES 
            (NOW() - INTERVAL '1 hour', '{symbol}', '1h', 50000, 50100, 49900, 50050, 100, 'sample'),
            (NOW() - INTERVAL '2 hours', '{symbol}', '1h', 49950, 50000, 49800, 50000, 120, 'sample'),
            (NOW() - INTERVAL '3 hours', '{symbol}', '1h', 49800, 49950, 49700, 49950, 90, 'sample')
            ON CONFLICT DO NOTHING;
        """)
    
    print("✅ 시장 데이터 테이블 생성 완료!")

def downgrade() -> None:
    """시장 데이터 테이블 제거"""
    
    print("🗑️ 시장 데이터 테이블 제거 중...")
    
    # =================================================================
    # 1. 압축 정책 제거
    # =================================================================
    
    print("🗜️ 압축 정책 제거 중...")
    
    # 압축 정책들 제거
    op.execute("""
        SELECT remove_compression_policy('market_data.price_data', if_not_exists => true);
    """)
    
    op.execute("""
        SELECT remove_compression_policy('market_data.orderbook_data', if_not_exists => true);
    """)
    
    # =================================================================
    # 2. 하이퍼테이블 제거 (테이블 제거 전에 필요)
    # =================================================================
    
    print("🕐 하이퍼테이블 해제 중...")
    
    # TimescaleDB 하이퍼테이블 해제는 테이블 DROP으로 자동 처리됨
    
    # =================================================================
    # 3. 테이블 제거 (역순)
    # =================================================================
    
    print("📊 테이블 제거 중...")
    
    # trade_ticks 테이블 제거
    op.drop_table('trade_ticks', schema='market_data')
    print("✅ trade_ticks 테이블 제거 완료")
    
    # orderbook_data 테이블 제거
    op.drop_table('orderbook_data', schema='market_data')
    print("✅ orderbook_data 테이블 제거 완료")
    
    # price_data 테이블 제거
    op.drop_table('price_data', schema='market_data')
    print("✅ price_data 테이블 제거 완료")
    
    print("✅ 시장 데이터 테이블 롤백 완료")