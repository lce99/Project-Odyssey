"""Create analysis tables

Revision ID: 003_analysis_tables
Revises: 002_market_data_tables
Create Date: 2024-01-01 00:02:00.000000

페어 분석 및 신호 생성을 위한 테이블들을 생성합니다:
- trading_pairs: 발견된 페어 정보 및 공적분 결과
- kalman_states: 칼만 필터 상태 (헤지비율, Z-score 등)
- market_regime_filters: 시장 국면 필터 결과
- ml_predictions: 머신러닝 모델 예측 결과
- signals: 최종 거래 신호

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_analysis_tables'
down_revision = '002_market_data_tables'
branch_labels = None
depends_on = None

def get_env_policies():
    """환경별 정책 가져오기"""
    from alembic import context
    return getattr(context, '_env_policies', {
        'compression_after': 'INTERVAL \'7 days\'',
        'analysis_retention': 'INTERVAL \'1 year\'',
    })

def upgrade() -> None:
    """분석 관련 테이블 생성"""
    
    print("🧠 분석 테이블 생성 중...")
    
    # =================================================================
    # 1. trading_pairs 테이블 생성 (페어 정보의 마스터)
    # =================================================================
    
    print("👥 trading_pairs 테이블 생성 중...")
    
    op.create_table(
        'trading_pairs',
        # Primary Key
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), 
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='페어 고유 ID'),
        
        # 페어 구성 자산
        sa.Column('symbol_a', sa.String(20), nullable=False,
                  comment='첫 번째 자산 (예: BTC/USDT)'),
        sa.Column('symbol_b', sa.String(20), nullable=False,
                  comment='두 번째 자산 (예: ETH/USDT)'),
        
        # 페어 기본 정보
        sa.Column('pair_name', sa.String(50), nullable=False,
                  comment='페어 표시명 (BTC/USDT_ETH/USDT)'),
        sa.Column('cluster_id', sa.Integer, nullable=True,
                  comment='K-Means 클러스터 ID'),
        
        # 공적분 검증 결과
        sa.Column('cointegration_pvalue', sa.Numeric(10, 6), nullable=True,
                  comment='Engle-Granger 공적분 p-value'),
        sa.Column('cointegration_statistic', sa.Numeric(10, 6), nullable=True,
                  comment='공적분 검정 통계량'),
        
        # 페어 상태 관리
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true',
                  comment='활성 거래 페어 여부'),
        sa.Column('status', sa.String(20), nullable=False, server_default='discovered',
                  comment='페어 상태'),
        
        # 시간 추적
        sa.Column('discovered_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()'),
                  comment='페어 발견 일시'),
        sa.Column('last_validated_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()'),
                  comment='마지막 검증 일시'),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('pair_id'),
        sa.UniqueConstraint('symbol_a', 'symbol_b', name='unique_pair_combination'),
        sa.CheckConstraint('symbol_a != symbol_b', name='different_symbols'),
        sa.CheckConstraint("status IN ('discovered', 'backtested', 'live', 'paused', 'archived')", 
                          name='valid_pair_status'),
        sa.CheckConstraint('cointegration_pvalue >= 0 AND cointegration_pvalue <= 1', 
                          name='valid_pvalue_range'),
        
        schema='analysis',
        comment='발견된 거래 페어 정보 및 공적분 검증 결과'
    )
    
    # =================================================================
    # 2. kalman_states 테이블 생성 (시계열)
    # =================================================================
    
    print("🔄 kalman_states 테이블 생성 중...")
    
    op.create_table(
        'kalman_states',
        # 시간 (파티셔닝 키)
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='칼만 필터 계산 시간'),
        
        # 페어 참조
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        
        # 칼만 필터 상태 변수들
        sa.Column('hedge_ratio', sa.Numeric(12, 6), nullable=False,
                  comment='헤지 비율 (Beta)'),
        sa.Column('spread', sa.Numeric(20, 8), nullable=False,
                  comment='스프레드 값'),
        sa.Column('z_score', sa.Numeric(8, 4), nullable=False,
                  comment='Z-score (정규화된 스프레드)'),
        
        # 칼만 필터 내부 상태
        sa.Column('state_mean', sa.Numeric(12, 6), nullable=True,
                  comment='상태 평균'),
        sa.Column('state_covariance', sa.Numeric(12, 6), nullable=True,
                  comment='상태 공분산'),
        
        # 통계적 메트릭
        sa.Column('spread_mean', sa.Numeric(20, 8), nullable=True,
                  comment='스프레드 이동평균'),
        sa.Column('spread_std', sa.Numeric(20, 8), nullable=True,
                  comment='스프레드 표준편차'),
        sa.Column('half_life', sa.Numeric(8, 2), nullable=True,
                  comment='평균 회귀 반감기 (일)'),
        
        # 메타데이터
        sa.Column('lookback_period', sa.Integer, nullable=False, server_default='100',
                  comment='계산에 사용된 lookback 기간'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.CheckConstraint('lookback_period > 0', name='positive_lookback'),
        sa.CheckConstraint('spread_std >= 0', name='positive_std'),
        sa.CheckConstraint('half_life > 0', name='positive_half_life'),
        
        schema='analysis',
        comment='칼만 필터 상태 및 통계적 메트릭'
    )
    
    # 외래키 제약 조건 (별도 추가)
    op.create_foreign_key(
        'fk_kalman_states_pair_id',
        'kalman_states', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='analysis', referent_schema='analysis'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 kalman_states를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'analysis.kalman_states', 
            'time',
            chunk_time_interval => INTERVAL '1 day'
        );
    """)
    
    # =================================================================
    # 3. market_regime_filters 테이블 생성
    # =================================================================
    
    print("🌍 market_regime_filters 테이블 생성 중...")
    
    op.create_table(
        'market_regime_filters',
        # 시간
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='필터 계산 시간'),
        
        # 대표 자산
        sa.Column('representative_asset', sa.String(20), nullable=False, 
                  server_default='BTC/USDT',
                  comment='시장 국면 판단 대표 자산'),
        
        # 추세 필터 결과
        sa.Column('trend_filter_active', sa.Boolean, nullable=True,
                  comment='상승 추세 여부'),
        sa.Column('price_vs_ema200', sa.Numeric(8, 4), nullable=True,
                  comment='현재가/EMA200 비율'),
        sa.Column('ema_slope', sa.Numeric(8, 6), nullable=True,
                  comment='EMA 기울기'),
        
        # 변동성 필터 결과 (GARCH)
        sa.Column('volatility_filter_active', sa.Boolean, nullable=True,
                  comment='낮은 변동성 여부'),
        sa.Column('predicted_volatility', sa.Numeric(8, 6), nullable=True,
                  comment='GARCH 예측 변동성'),
        sa.Column('volatility_percentile', sa.Numeric(5, 2), nullable=True,
                  comment='과거 대비 변동성 백분위'),
        
        # 거래량 필터 결과
        sa.Column('volume_filter_active', sa.Boolean, nullable=True,
                  comment='충분한 거래량 여부'),
        sa.Column('volume_ratio', sa.Numeric(8, 4), nullable=True,
                  comment='평균 거래량 대비 비율'),
        
        # 통합 필터 결과
        sa.Column('regime_is_favorable', sa.Boolean, nullable=True,
                  comment='전체 국면이 유리한지'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.CheckConstraint('price_vs_ema200 > 0', name='positive_price_ratio'),
        sa.CheckConstraint('predicted_volatility >= 0', name='positive_volatility'),
        sa.CheckConstraint('volatility_percentile >= 0 AND volatility_percentile <= 100', 
                          name='valid_percentile'),
        sa.CheckConstraint('volume_ratio > 0', name='positive_volume_ratio'),
        
        schema='analysis',
        comment='시장 국면 필터 결과 (추세, 변동성, 거래량)'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 market_regime_filters를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'analysis.market_regime_filters', 
            'time',
            chunk_time_interval => INTERVAL '1 day'
        );
    """)
    
    # =================================================================
    # 4. ml_predictions 테이블 생성
    # =================================================================
    
    print("🤖 ml_predictions 테이블 생성 중...")
    
    op.create_table(
        'ml_predictions',
        # Primary Key
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='예측 고유 ID'),
        
        # 시간 및 페어
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='예측 생성 시간'),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        
        # 입력 피처들
        sa.Column('z_score', sa.Numeric(8, 4), nullable=False,
                  comment='입력 Z-score'),
        sa.Column('spread_momentum', sa.Numeric(8, 6), nullable=True,
                  comment='스프레드 모멘텀'),
        sa.Column('volatility_ratio', sa.Numeric(8, 4), nullable=True,
                  comment='변동성 비율'),
        sa.Column('volume_ratio', sa.Numeric(8, 4), nullable=True,
                  comment='거래량 비율'),
        sa.Column('time_of_day', sa.Integer, nullable=True,
                  comment='시간 피처 (0-23)'),
        
        # 모델 예측 결과
        sa.Column('mean_reversion_probability', sa.Numeric(5, 4), nullable=True,
                  comment='평균 회귀 성공 확률'),
        sa.Column('predicted_return_1d', sa.Numeric(8, 6), nullable=True,
                  comment='1일 예상 수익률'),
        sa.Column('predicted_return_7d', sa.Numeric(8, 6), nullable=True,
                  comment='7일 예상 수익률'),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True,
                  comment='예측 신뢰도'),
        
        # 모델 메타데이터
        sa.Column('model_version', sa.String(20), nullable=False,
                  comment='모델 버전 (예: xgb_v1.2)'),
        sa.Column('model_type', sa.String(20), nullable=False, server_default='xgboost',
                  comment='모델 타입'),
        
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('prediction_id'),
        sa.CheckConstraint('mean_reversion_probability BETWEEN 0 AND 1', 
                          name='valid_probability'),
        sa.CheckConstraint('confidence_score BETWEEN 0 AND 1', 
                          name='valid_confidence'),
        sa.CheckConstraint('time_of_day BETWEEN 0 AND 23', 
                          name='valid_hour'),
        sa.CheckConstraint("model_type IN ('xgboost', 'lightgbm', 'catboost', 'neural_network')", 
                          name='valid_model_type'),
        
        schema='analysis',
        comment='머신러닝 모델 예측 결과'
    )
    
    # 외래키 제약 조건
    op.create_foreign_key(
        'fk_ml_predictions_pair_id',
        'ml_predictions', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='analysis', referent_schema='analysis'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 ml_predictions를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'analysis.ml_predictions', 
            'time',
            chunk_time_interval => INTERVAL '1 day'
        );
    """)
    
    # =================================================================
    # 5. signals 테이블 생성 (최종 거래 신호)
    # =================================================================
    
    print("📡 signals 테이블 생성 중...")
    
    op.create_table(
        'signals',
        # Primary Key
        sa.Column('signal_id', postgresql.UUID(as_uuid=True),
                  nullable=False, server_default=sa.text('uuid_generate_v4()'),
                  comment='신호 고유 ID'),
        
        # 시간 및 페어
        sa.Column('time', postgresql.TIMESTAMP(timezone=True), nullable=False,
                  comment='신호 생성 시간'),
        sa.Column('pair_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='거래 페어 ID'),
        
        # 신호 정보
        sa.Column('signal_type', sa.String(10), nullable=False,
                  comment='신호 타입 (LONG/SHORT/CLOSE/STOP)'),
        sa.Column('signal_strength', sa.Numeric(5, 4), nullable=True,
                  comment='신호 강도 (0-1)'),
        
        # 신호 생성 조건들
        sa.Column('z_score', sa.Numeric(8, 4), nullable=False,
                  comment='현재 Z-score'),
        sa.Column('z_score_threshold', sa.Numeric(5, 2), nullable=True,
                  comment='사용된 Z-score 임계값'),
        sa.Column('regime_filter_passed', sa.Boolean, nullable=True,
                  comment='국면 필터 통과 여부'),
        sa.Column('ml_probability', sa.Numeric(5, 4), nullable=True,
                  comment='ML 모델 확률'),
        sa.Column('ml_threshold', sa.Numeric(5, 4), nullable=True,
                  comment='ML 임계값'),
        
        # 신호 상태 관리
        sa.Column('is_executed', sa.Boolean, nullable=False, server_default='false',
                  comment='실행 여부'),
        sa.Column('is_valid', sa.Boolean, nullable=False, server_default='true',
                  comment='신호 유효성'),
        sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), nullable=True,
                  comment='신호 만료 시간'),
        
        # 메타데이터
        sa.Column('created_by', sa.String(50), nullable=False, server_default='signal_generator',
                  comment='생성 모듈'),
        sa.Column('notes', sa.Text, nullable=True,
                  comment='추가 설명'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')),
        
        # 제약 조건
        sa.PrimaryKeyConstraint('signal_id'),
        sa.CheckConstraint("signal_type IN ('LONG', 'SHORT', 'CLOSE', 'STOP')", 
                          name='valid_signal_type'),
        sa.CheckConstraint('signal_strength BETWEEN 0 AND 1', 
                          name='valid_signal_strength'),
        sa.CheckConstraint('z_score_threshold > 0', 
                          name='positive_z_threshold'),
        sa.CheckConstraint('ml_probability BETWEEN 0 AND 1', 
                          name='valid_ml_probability'),
        sa.CheckConstraint('ml_threshold BETWEEN 0 AND 1', 
                          name='valid_ml_threshold'),
        
        schema='analysis',
        comment='최종 거래 신호'
    )
    
    # 외래키 제약 조건
    op.create_foreign_key(
        'fk_signals_pair_id',
        'signals', 'trading_pairs',
        ['pair_id'], ['pair_id'],
        source_schema='analysis', referent_schema='analysis'
    )
    
    # TimescaleDB 하이퍼테이블 변환
    print("🕐 signals를 하이퍼테이블로 변환 중...")
    op.execute("""
        SELECT create_hypertable(
            'analysis.signals', 
            'time',
            chunk_time_interval => INTERVAL '1 day'
        );
    """)
    
    # =================================================================
    # 6. 인덱스 생성 (성능 최적화)
    # =================================================================
    
    print("🔍 분석 테이블 인덱스 생성 중...")
    
    # trading_pairs 인덱스
    op.execute("""
        CREATE INDEX idx_trading_pairs_active_status 
        ON analysis.trading_pairs (is_active, status);
    """)
    
    op.execute("""
        CREATE INDEX idx_trading_pairs_symbols 
        ON analysis.trading_pairs (symbol_a, symbol_b);
    """)
    
    # kalman_states 핵심 인덱스들
    op.execute("""
        CREATE INDEX idx_kalman_states_pair_time 
        ON analysis.kalman_states (pair_id, time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_kalman_states_latest 
        ON analysis.kalman_states (time DESC, pair_id);
    """)
    
    # Z-score 기반 신호 탐지용 (중요!)
    op.execute("""
        CREATE INDEX idx_kalman_states_z_score 
        ON analysis.kalman_states (time DESC, abs(z_score) DESC) 
        WHERE abs(z_score) >= 2.0;
    """)
    
    # market_regime_filters 인덱스
    op.execute("""
        CREATE INDEX idx_market_regime_time_favorable 
        ON analysis.market_regime_filters (time DESC, regime_is_favorable);
    """)
    
    # ml_predictions 인덱스
    op.execute("""
        CREATE INDEX idx_ml_predictions_pair_time 
        ON analysis.ml_predictions (pair_id, time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_ml_predictions_probability 
        ON analysis.ml_predictions (time DESC, mean_reversion_probability DESC)
        WHERE mean_reversion_probability >= 0.5;
    """)
    
    # signals 핵심 인덱스들
    op.execute("""
        CREATE INDEX idx_signals_time_valid 
        ON analysis.signals (time DESC) 
        WHERE is_valid = TRUE;
    """)
    
    op.execute("""
        CREATE INDEX idx_signals_pair_execution 
        ON analysis.signals (pair_id, is_executed, time DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_signals_type_strength 
        ON analysis.signals (signal_type, signal_strength DESC, time DESC)
        WHERE is_valid = TRUE AND is_executed = FALSE;
    """)
    
    # =================================================================
    # 7. 압축 정책 적용
    # =================================================================
    
    print("🗜️ 분석 테이블 압축 정책 적용 중...")
    
    policies = get_env_policies()
    compression_after = policies.get('compression_after', 'INTERVAL \'7 days\'')
    
    # 시계열 테이블들에 압축 정책 적용
    for table in ['kalman_states', 'market_regime_filters', 'ml_predictions', 'signals']:
        op.execute(f"""
            SELECT add_compression_policy(
                'analysis.{table}', 
                {compression_after}
            );
        """)
        print(f"✅ {table} 압축 정책 적용 완료")
    
    # =================================================================
    # 8. 샘플 데이터 삽입 (테스트용)
    # =================================================================
    
    print("📝 분석 테이블 샘플 데이터 삽입 중...")
    
    # 기본 거래 페어들
    sample_pairs = [
        ('BTC/USDT', 'ETH/USDT', 'BTC/USDT_ETH/USDT'),
        ('ETH/USDT', 'BNB/USDT', 'ETH/USDT_BNB/USDT'),
        ('ADA/USDT', 'DOT/USDT', 'ADA/USDT_DOT/USDT')
    ]
    
    for symbol_a, symbol_b, pair_name in sample_pairs:
        op.execute(f"""
            INSERT INTO analysis.trading_pairs (symbol_a, symbol_b, pair_name, is_active, status)
            VALUES ('{symbol_a}', '{symbol_b}', '{pair_name}', TRUE, 'discovered')
            ON CONFLICT (symbol_a, symbol_b) DO NOTHING;
        """)
    
    # 시장 국면 필터 샘플 데이터
    op.execute("""
        INSERT INTO analysis.market_regime_filters 
        (time, representative_asset, trend_filter_active, volatility_filter_active, 
         volume_filter_active, regime_is_favorable)
        VALUES 
        (NOW() - INTERVAL '1 hour', 'BTC/USDT', TRUE, TRUE, TRUE, TRUE),
        (NOW() - INTERVAL '2 hours', 'BTC/USDT', TRUE, FALSE, TRUE, FALSE),
        (NOW() - INTERVAL '3 hours', 'BTC/USDT', FALSE, TRUE, TRUE, FALSE)
        ON CONFLICT DO NOTHING;
    """)
    
    print("✅ 분석 테이블 생성 완료!")

def downgrade() -> None:
    """분석 테이블 제거"""
    
    print("🗑️ 분석 테이블 제거 중...")
    
    # =================================================================
    # 1. 압축 정책 제거
    # =================================================================
    
    print("🗜️ 압축 정책 제거 중...")
    
    for table in ['kalman_states', 'market_regime_filters', 'ml_predictions', 'signals']:
        op.execute(f"""
            SELECT remove_compression_policy('analysis.{table}', if_not_exists => true);
        """)
    
    # =================================================================
    # 2. 외래키 제약 조건 제거 (테이블 제거 전)
    # =================================================================
    
    print("🔗 외래키 제약 조건 제거 중...")
    
    # signals 테이블의 외래키
    op.drop_constraint('fk_signals_pair_id', 'signals', schema='analysis', type_='foreignkey')
    
    # ml_predictions 테이블의 외래키
    op.drop_constraint('fk_ml_predictions_pair_id', 'ml_predictions', schema='analysis', type_='foreignkey')
    
    # kalman_states 테이블의 외래키
    op.drop_constraint('fk_kalman_states_pair_id', 'kalman_states', schema='analysis', type_='foreignkey')
    
    # =================================================================
    # 3. 테이블 제거 (의존성 역순)
    # =================================================================
    
    print("📊 분석 테이블 제거 중...")
    
    # 의존성이 있는 테이블들부터 제거
    tables_to_drop = [
        'signals',           # 신호 테이블
        'ml_predictions',    # ML 예측 테이블  
        'market_regime_filters',  # 시장 국면 필터
        'kalman_states',     # 칼만 상태 테이블
        'trading_pairs'      # 페어 마스터 테이블 (마지막)
    ]
    
    for table in tables_to_drop:
        op.drop_table(table, schema='analysis')
        print(f"✅ {table} 테이블 제거 완료")
    
    print("✅ 분석 테이블 롤백 완료")