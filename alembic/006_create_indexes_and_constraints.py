# =============================================================================
# 006 - 추가 인덱스 및 제약조건 최적화
# =============================================================================

"""Additional indexes and constraints optimization

Revision ID: 006_indexes_constraints
Revises: 005_monitoring_tables
Create Date: 2024-01-01 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006_indexes_constraints'
down_revision = '005_monitoring_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """추가 인덱스 및 제약조건 최적화"""
    
    print("🎯 고급 인덱스 및 제약조건 생성 중...")
    
    # =================================================================
    # 1. 복합 인덱스 (성능 크리티컬)
    # =================================================================
    
    # 페어별 최신 칼만 상태 조회 최적화 (가장 빈번한 쿼리)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_kalman_latest_by_pair
        ON analysis.kalman_states (pair_id, time DESC)
        INCLUDE (z_score, hedge_ratio, spread);
    """)
    
    # 신호 실행 대기 목록 최적화
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_signals_pending_execution
        ON analysis.signals (time DESC, signal_strength DESC)
        WHERE is_valid = TRUE AND is_executed = FALSE AND expires_at > NOW();
    """)
    
    # 리스크 관리용 포지션 모니터링
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_positions_risk_monitoring
        ON trading.positions (last_updated DESC, current_z_score, stop_loss_z_score)
        WHERE status = 'OPEN' AND current_z_score IS NOT NULL;
    """)
    
    # =================================================================
    # 2. 부분 인덱스 (저장공간 최적화)
    # =================================================================
    
    # 최근 30일 거래만 인덱싱
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_trades_recent_performance
        ON trading.trades (pair_id, execution_time DESC, net_pnl_usd DESC)
        WHERE execution_time >= NOW() - INTERVAL '30 days' AND trade_type = 'CLOSE';
    """)
    
    # 높은 Z-score만 인덱싱 (신호 생성용)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_kalman_high_z_scores
        ON analysis.kalman_states (time DESC, pair_id, abs(z_score) DESC)
        WHERE abs(z_score) >= 2.0;
    """)
    
    # =================================================================
    # 3. 함수 기반 인덱스
    # =================================================================
    
    # 절대값 Z-score 인덱스 (신호 강도 순)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_kalman_abs_z_score
        ON analysis.kalman_states (time DESC, (abs(z_score)) DESC);
    """)
    
    # 포지션 보유 기간 계산 인덱스
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_positions_holding_period
        ON trading.positions (
            (EXTRACT(DAYS FROM NOW() - entry_time))::INTEGER DESC
        ) WHERE status = 'OPEN';
    """)
    
    # =================================================================
    # 4. 고급 제약조건
    # =================================================================
    
    # 페어별 동시 보유 포지션 수 제한 (최대 1개)
    op.execute("""
        CREATE UNIQUE INDEX CONCURRENTLY idx_one_position_per_pair
        ON trading.positions (pair_id)
        WHERE status = 'OPEN';
    """)
    
    # 일일 거래 횟수 제한을 위한 준비 (뷰에서 활용)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_trades_daily_count
        ON trading.trades (DATE(execution_time), pair_id);
    """)
    
    print("✅ 고급 인덱스 및 제약조건 생성 완료")

def downgrade() -> None:
    """인덱스 제거"""
    indexes_to_drop = [
        'idx_kalman_latest_by_pair',
        'idx_signals_pending_execution', 
        'idx_positions_risk_monitoring',
        'idx_trades_recent_performance',
        'idx_kalman_high_z_scores',
        'idx_kalman_abs_z_score',
        'idx_positions_holding_period',
        'idx_one_position_per_pair',
        'idx_trades_daily_count'
    ]
    
    for idx in indexes_to_drop:
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx};")
