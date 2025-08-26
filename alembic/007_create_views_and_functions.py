# =============================================================================
# 007 - 뷰 및 함수 생성
# =============================================================================

"""Create views and utility functions

Revision ID: 007_views_functions  
Revises: 006_indexes_constraints
Create Date: 2024-01-01 00:06:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '007_views_functions'
down_revision = '006_indexes_constraints'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """뷰 및 유틸리티 함수 생성"""
    
    print("👁️ 뷰 및 함수 생성 중...")
    
    # =================================================================
    # 1. 핵심 비즈니스 뷰들
    # =================================================================
    
    # 활성 페어의 현재 상태 (가장 중요한 뷰)
    op.execute("""
        CREATE VIEW analysis.active_pairs_current_state AS
        SELECT DISTINCT ON (tp.pair_id)
            tp.pair_id,
            tp.pair_name,
            tp.symbol_a,
            tp.symbol_b,
            tp.status as pair_status,
            ks.time as last_kalman_update,
            ks.hedge_ratio,
            ks.spread,
            ks.z_score,
            ks.half_life,
            -- 포지션 정보
            pos.position_id,
            pos.side as position_side,
            pos.current_pnl_usd,
            pos.entry_time as position_entry_time,
            -- 시장 국면
            mrf.regime_is_favorable,
            -- 최신 ML 예측
            mlp.mean_reversion_probability
        FROM analysis.trading_pairs tp
        LEFT JOIN analysis.kalman_states ks ON tp.pair_id = ks.pair_id
        LEFT JOIN trading.positions pos ON tp.pair_id = pos.pair_id AND pos.status = 'OPEN'
        LEFT JOIN analysis.market_regime_filters mrf ON mrf.time >= NOW() - INTERVAL '1 hour'
        LEFT JOIN analysis.ml_predictions mlp ON tp.pair_id = mlp.pair_id AND mlp.time >= NOW() - INTERVAL '1 hour'
        WHERE tp.is_active = TRUE
        ORDER BY tp.pair_id, ks.time DESC;
    """)
    
    # 페어별 신호 강도 랭킹
    op.execute("""
        CREATE VIEW analysis.pair_signal_ranking AS
        SELECT 
            tp.pair_id,
            tp.pair_name,
            ks.z_score,
            ABS(ks.z_score) as abs_z_score,
            mlp.mean_reversion_probability,
            mrf.regime_is_favorable,
            -- 종합 신호 점수
            CASE 
                WHEN mrf.regime_is_favorable AND ABS(ks.z_score) >= 2.0 
                THEN ABS(ks.z_score) * COALESCE(mlp.mean_reversion_probability, 0.5)
                ELSE 0
            END as composite_signal_score,
            ks.time as last_updated
        FROM analysis.active_pairs_current_state apcs
        JOIN analysis.trading_pairs tp ON apcs.pair_id = tp.pair_id  
        JOIN analysis.kalman_states ks ON tp.pair_id = ks.pair_id
        LEFT JOIN analysis.ml_predictions mlp ON tp.pair_id = mlp.pair_id 
        LEFT JOIN analysis.market_regime_filters mrf ON mrf.time >= NOW() - INTERVAL '1 hour'
        WHERE tp.is_active = TRUE
        ORDER BY composite_signal_score DESC;
    """)
    
    # 시스템 대시보드 뷰
    op.execute("""
        CREATE VIEW monitoring.system_dashboard AS
        SELECT 
            NOW() as dashboard_time,
            -- 페어 및 포지션 요약
            (SELECT COUNT(*) FROM analysis.trading_pairs WHERE is_active = TRUE) as active_pairs,
            (SELECT COUNT(*) FROM trading.positions WHERE status = 'OPEN') as open_positions,
            (SELECT COALESCE(SUM(current_pnl_usd), 0) FROM trading.positions WHERE status = 'OPEN') as unrealized_pnl,
            -- 오늘의 성과
            (SELECT COALESCE(total_pnl_usd, 0) FROM monitoring.daily_performance WHERE date = CURRENT_DATE) as today_pnl,
            (SELECT COALESCE(trades_closed, 0) FROM monitoring.daily_performance WHERE date = CURRENT_DATE) as today_trades,
            -- 데이터 상태
            (SELECT MAX(time) FROM market_data.price_data) as last_price_data,
            -- 시장 국면
            (SELECT regime_is_favorable FROM analysis.market_regime_filters ORDER BY time DESC LIMIT 1) as market_favorable;
    """)
    
    # =================================================================
    # 2. 유틸리티 함수들
    # =================================================================
    
    # 페어의 최근 가격 데이터 조회
    op.execute("""
        CREATE OR REPLACE FUNCTION get_pair_recent_prices(
            p_symbol_a VARCHAR(20),
            p_symbol_b VARCHAR(20), 
            p_timeframe VARCHAR(10) DEFAULT '1h',
            p_limit INTEGER DEFAULT 100
        ) RETURNS TABLE (
            time TIMESTAMPTZ,
            price_a DECIMAL(20,8),
            price_b DECIMAL(20,8)
        ) AS $
        BEGIN
            RETURN QUERY
            SELECT 
                pd_a.time,
                pd_a.close as price_a,
                pd_b.close as price_b
            FROM market_data.price_data pd_a
            JOIN market_data.price_data pd_b ON pd_a.time = pd_b.time
            WHERE pd_a.symbol = p_symbol_a 
                AND pd_b.symbol = p_symbol_b
                AND pd_a.timeframe = p_timeframe
                AND pd_b.timeframe = p_timeframe
            ORDER BY pd_a.time DESC
            LIMIT p_limit;
        END;
        $ LANGUAGE plpgsql;
    """)
    
    # 포트폴리오 요약 함수
    op.execute("""
        CREATE OR REPLACE FUNCTION get_portfolio_summary()
        RETURNS TABLE (
            total_positions INTEGER,
            total_unrealized_pnl DECIMAL(15,4),
            total_realized_pnl_today DECIMAL(15,4),
            max_z_score DECIMAL(8,4),
            favorable_regime_pairs INTEGER
        ) AS $
        BEGIN
            RETURN QUERY
            SELECT 
                (SELECT COUNT(*)::INTEGER FROM trading.positions WHERE status = 'OPEN'),
                (SELECT COALESCE(SUM(current_pnl_usd), 0) FROM trading.positions WHERE status = 'OPEN'),
                (SELECT COALESCE(SUM(net_pnl_usd), 0) FROM trading.trades WHERE DATE(execution_time) = CURRENT_DATE),
                (SELECT COALESCE(MAX(ABS(current_z_score)), 0) FROM trading.positions WHERE status = 'OPEN'),
                (SELECT COUNT(*)::INTEGER FROM analysis.active_pairs_current_state WHERE regime_is_favorable = TRUE);
        END;
        $ LANGUAGE plpgsql;
    """)
    
    print("✅ 뷰 및 함수 생성 완료")

def downgrade() -> None:
    """뷰 및 함수 제거"""
    # 뷰 제거
    op.execute("DROP VIEW IF EXISTS monitoring.system_dashboard;")
    op.execute("DROP VIEW IF EXISTS analysis.pair_signal_ranking;")  
    op.execute("DROP VIEW IF EXISTS analysis.active_pairs_current_state;")
    
    # 함수 제거
    op.execute("DROP FUNCTION IF EXISTS get_pair_recent_prices(VARCHAR, VARCHAR, VARCHAR, INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS get_portfolio_summary();")