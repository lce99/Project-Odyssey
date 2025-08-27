# config_refactored.py - Project Odysseus 완전 통합 Pydantic 설정
# 모든 설정을 Pydantic으로 통합하여 타입 안전성과 검증 강화

import os
from typing import List, Optional, Literal
from pathlib import Path
from enum import Enum
from pydantic import BaseSettings, BaseModel, validator, root_validator, Field
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# =============================================================================
# 열거형 정의 (허용된 값들)
# =============================================================================

class TradingMode(str, Enum):
    """거래 모드"""
    TESTNET = "testnet"
    LIVE = "live"

class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ExchangeType(str, Enum):
    """지원 거래소"""
    BINANCE = "binance"
    BYBIT = "bybit"

class MarketType(str, Enum):
    """마켓 타입"""
    SPOT = "spot"
    FUTURES = "futures"

class DataValidationPolicy(str, Enum):
    """데이터 검증 정책"""
    INTERPOLATE = "interpolate"
    EXCLUDE = "exclude"
    FORWARD_FILL = "forward_fill"

class OrderType(str, Enum):
    """주문 타입"""
    LIMIT = "limit"
    MARKET = "market"
    TWAP = "twap"

class PositionSizingMethod(str, Enum):
    """포지션 사이징 방법"""
    LINEAR = "linear"
    SQUARED = "squared"
    FIXED = "fixed"
    KELLY = "kelly"

# =============================================================================
# 세부 설정 Pydantic 모델들
# =============================================================================

class DatabaseSettings(BaseModel):
    """데이터베이스 설정"""
    
    host: str = Field(default="localhost", description="데이터베이스 호스트")
    port: int = Field(default=5432, ge=1, le=65535, description="데이터베이스 포트")
    database: str = Field(min_length=1, description="데이터베이스 이름")
    user: str = Field(min_length=1, description="데이터베이스 사용자")
    password: str = Field(min_length=8, description="데이터베이스 비밀번호")
    
    # 테이블 이름들
    table_price_data: str = Field(default="price_data", description="가격 데이터 테이블")
    table_orderbook_data: str = Field(default="orderbook_data", description="오더북 데이터 테이블")
    table_pair_analysis: str = Field(default="pair_analysis", description="페어 분석 테이블")
    table_signals: str = Field(default="signals", description="신호 테이블")
    table_trades: str = Field(default="trades", description="거래 테이블")
    table_positions: str = Field(default="positions", description="포지션 테이블")
    
    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('데이터베이스 비밀번호는 8자 이상이어야 합니다')
        if v in ['password', '123456', 'admin', 'root']:
            raise ValueError('약한 비밀번호는 사용할 수 없습니다')
        return v

class ExchangeSettings(BaseModel):
    """거래소 설정"""
    
    binance_api_key: Optional[str] = Field(default=None, description="Binance API 키")
    binance_secret_key: Optional[str] = Field(default=None, description="Binance Secret 키")
    bybit_api_key: Optional[str] = Field(default=None, description="Bybit API 키")
    bybit_secret_key: Optional[str] = Field(default=None, description="Bybit Secret 키")
    
    primary_exchange: ExchangeType = Field(default=ExchangeType.BINANCE, description="주 거래소")
    market_type: MarketType = Field(default=MarketType.SPOT, description="마켓 타입")
    
    # 수수료 설정
    spot_maker_fee: float = Field(default=0.001, ge=0, le=0.01, description="현물 Maker 수수료")
    spot_taker_fee: float = Field(default=0.001, ge=0, le=0.01, description="현물 Taker 수수료")
    futures_maker_fee: float = Field(default=0.0002, ge=0, le=0.01, description="선물 Maker 수수료")
    futures_taker_fee: float = Field(default=0.0005, ge=0, le=0.01, description="선물 Taker 수수료")
    
    @root_validator
    def validate_exchange_keys(cls, values):
        """최소 하나의 거래소 API 키는 필수"""
        binance_key = values.get('binance_api_key')
        binance_secret = values.get('binance_secret_key') 
        bybit_key = values.get('bybit_api_key')
        bybit_secret = values.get('bybit_secret_key')
        
        has_binance = binance_key and binance_secret
        has_bybit = bybit_key and bybit_secret
        
        if not (has_binance or has_bybit):
            raise ValueError('최소 하나의 거래소 API 키 쌍이 필요합니다')
        
        # primary_exchange 자동 설정
        if has_binance and not has_bybit:
            values['primary_exchange'] = ExchangeType.BINANCE
        elif has_bybit and not has_binance:
            values['primary_exchange'] = ExchangeType.BYBIT
            
        return values

class DataCollectionSettings(BaseModel):
    """데이터 수집 설정"""
    
    validation_policy: DataValidationPolicy = Field(default=DataValidationPolicy.INTERPOLATE)
    historical_data_start: str = Field(default="2022-01-01", description="과거 데이터 시작일")
    historical_timeframes: List[str] = Field(default=["1h", "4h", "1d"], description="수집할 시간대")
    default_timeframe: str = Field(default="1h", description="기본 시간대")
    
    realtime_data_interval: int = Field(default=5, ge=1, le=60, description="실시간 데이터 수집 간격(초)")
    websocket_timeout: int = Field(default=30, ge=10, le=300, description="WebSocket 타임아웃(초)")
    
    max_price_deviation: float = Field(default=0.1, ge=0.01, le=1.0, description="최대 가격 변동률")
    max_missing_data_ratio: float = Field(default=0.05, ge=0.01, le=0.5, description="최대 데이터 누락률")

class PairSearchSettings(BaseModel):
    """페어 탐색 설정"""
    
    re_search_schedule: Literal["daily", "weekly", "monthly"] = Field(default="weekly")
    top_n_assets_for_universe: int = Field(default=50, ge=10, le=200)
    min_market_cap_rank: int = Field(default=100, ge=1, le=1000)
    min_daily_volume_usd: float = Field(default=10_000_000, ge=1_000_000)
    exclude_stablecoins: bool = Field(default=True)
    
    k_means_n_clusters: int = Field(default=5, ge=2, le=20)
    cointegration_p_value_threshold: float = Field(default=0.05, ge=0.01, le=0.1)
    cointegration_lookback_days: int = Field(default=252, ge=30, le=1000)
    min_correlation: float = Field(default=0.7, ge=0.3, le=0.99)
    max_correlation: float = Field(default=0.95, ge=0.8, le=0.99)
    
    @validator('max_correlation')
    def validate_correlation_range(cls, v, values):
        if 'min_correlation' in values and v <= values['min_correlation']:
            raise ValueError('max_correlation은 min_correlation보다 커야 합니다')
        return v

class KalmanFilterSettings(BaseModel):
    """칼만 필터 설정"""
    
    transition_covariance: float = Field(default=0.01, gt=0, le=1, description="Q: 과정 노이즈")
    observation_covariance: float = Field(default=0.1, gt=0, le=1, description="R: 관측 노이즈")
    initial_state_covariance: float = Field(default=1.0, gt=0, le=10, description="P0: 초기 상태 공분산")
    lookback_period: int = Field(default=100, ge=50, le=500, description="초기화용 데이터 기간")
    update_frequency: str = Field(default="1h", description="업데이트 주기")

class TrendFilterSettings(BaseModel):
    """추세 필터 설정"""
    
    ema_period: int = Field(default=200, ge=50, le=500)
    ema_short_period: int = Field(default=50, ge=10, le=200)
    trend_strength_threshold: float = Field(default=0.02, ge=0.01, le=0.1)

class VolatilityFilterSettings(BaseModel):
    """변동성 필터 설정"""
    
    garch_p: int = Field(default=1, ge=1, le=5)
    garch_q: int = Field(default=1, ge=1, le=5)
    lookback_days: int = Field(default=90, ge=30, le=365)
    threshold_percentile: int = Field(default=80, ge=50, le=95)
    min_volatility: float = Field(default=0.01, ge=0.001, le=0.1)
    max_volatility: float = Field(default=0.15, ge=0.05, le=1.0)

class VolumeFilterSettings(BaseModel):
    """거래량 필터 설정"""
    
    lookback_period: int = Field(default=30, ge=7, le=90)
    min_volume_ratio: float = Field(default=0.5, ge=0.1, le=2.0)

class MarketRegimeSettings(BaseModel):
    """시장 국면 필터 설정"""
    
    representative_asset: str = Field(default="BTC/USDT", description="대표 자산")
    trend_filter: TrendFilterSettings = TrendFilterSettings()
    volatility_filter: VolatilityFilterSettings = VolatilityFilterSettings()
    volume_filter: VolumeFilterSettings = VolumeFilterSettings()

class SignalGenerationSettings(BaseModel):
    """신호 생성 설정"""
    
    z_score_entry_threshold: float = Field(default=2.0, ge=1.5, le=5.0)
    z_score_exit_threshold: float = Field(default=0.5, ge=0.1, le=1.5)
    z_score_stop_loss_threshold: float = Field(default=3.5, ge=2.0, le=6.0)
    ml_model_probability_threshold: float = Field(default=0.75, ge=0.5, le=0.95)
    min_signal_gap_hours: int = Field(default=4, ge=1, le=24)
    signal_decay_hours: int = Field(default=24, ge=6, le=168)
    require_all_filters: bool = Field(default=True)

class MLModelSettings(BaseModel):
    """머신러닝 모델 설정"""
    
    model_type: Literal["xgboost", "lightgbm", "catboost"] = Field(default="xgboost")
    model_path: Path = Field(default=Path("./ml_models/models/"))
    feature_lookback_periods: List[int] = Field(default=[5, 10, 20, 50])
    retrain_frequency: Literal["weekly", "monthly", "quarterly"] = Field(default="monthly")
    min_training_samples: int = Field(default=1000, ge=100, le=10000)
    validation_split: float = Field(default=0.2, ge=0.1, le=0.5)
    
    # XGBoost 하이퍼파라미터
    n_estimators: int = Field(default=100, ge=10, le=1000)
    max_depth: int = Field(default=6, ge=3, le=15)
    learning_rate: float = Field(default=0.1, ge=0.01, le=0.5)
    random_state: int = Field(default=42)

class StopLossSettings(BaseModel):
    """손절매 설정"""
    
    z_score_threshold: float = Field(default=3.5, ge=2.0, le=6.0, description="Z-score 손절 임계값")
    time_limit_hours: int = Field(default=240, ge=24, le=720, description="시간 기반 손절(시간)")
    drawdown_threshold: float = Field(default=0.05, ge=0.01, le=0.2, description="페어별 최대 손실률")

class PositionLimitsSettings(BaseModel):
    """포지션 제한 설정"""
    
    max_pairs_simultaneous: int = Field(default=5, ge=1, le=20, description="동시 보유 최대 페어 수")
    correlation_limit: float = Field(default=0.8, ge=0.3, le=0.95, description="포지션 간 상관관계 제한")

class DailyLimitsSettings(BaseModel):
    """일일 제한 설정"""
    
    max_daily_trades: int = Field(default=20, ge=1, le=100, description="일일 최대 거래 수")
    max_daily_loss: float = Field(default=0.02, ge=0.001, le=0.1, description="일일 최대 손실률")
    cooling_period_hours: int = Field(default=1, ge=0, le=24, description="손실 후 대기 시간")

class RiskManagementSettings(BaseModel):
    """리스크 관리 설정"""
    
    stop_loss: StopLossSettings = StopLossSettings()
    position_limits: PositionLimitsSettings = PositionLimitsSettings()
    daily_limits: DailyLimitsSettings = DailyLimitsSettings()

class PositionSizingSettings(BaseModel):
    """포지션 사이징 설정"""
    
    method: PositionSizingMethod = Field(default=PositionSizingMethod.LINEAR)
    max_position_per_pair: float = Field(default=0.1, ge=0.01, le=0.5, description="페어당 최대 자본 비중")
    max_total_exposure: float = Field(default=0.5, ge=0.1, le=1.0, description="전체 최대 노출")
    min_position_size_usd: float = Field(default=20, ge=5, le=1000, description="최소 포지션 크기")
    max_position_size_usd: float = Field(default=100, ge=10, le=10000, description="최대 포지션 크기")
    leverage: float = Field(default=1.0, ge=1.0, le=10.0, description="레버리지 (현물=1.0)")
    
    @validator('max_total_exposure')
    def validate_exposure_consistency(cls, v, values):
        if 'max_position_per_pair' in values:
            if v < values['max_position_per_pair']:
                raise ValueError('전체 최대 노출이 페어당 최대 노출보다 작을 수 없습니다')
        return v

class OrderExecutionSettings(BaseModel):
    """주문 실행 설정"""
    
    order_type: OrderType = Field(default=OrderType.LIMIT)
    slippage_protection: bool = Field(default=True)
    max_slippage_bps: int = Field(default=10, ge=1, le=100, description="최대 슬리피지(bp)")
    order_timeout_seconds: int = Field(default=60, ge=10, le=300, description="주문 타임아웃")
    partial_fill_threshold: float = Field(default=0.8, ge=0.5, le=1.0, description="부분 체결 임계값")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="재시도 횟수")
    twap_intervals: int = Field(default=5, ge=2, le=20, description="TWAP 분할 횟수")

class LoggingSettings(BaseModel):
    """로깅 설정"""
    
    level: LogLevel = Field(default=LogLevel.INFO)
    log_to_file: bool = Field(default=True)
    log_file_path: Path = Field(default=Path("./logs/"))
    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    backup_count: int = Field(default=5, ge=1, le=20)
    log_format: str = Field(default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}")
    separate_error_log: bool = Field(default=True)
    performance_log: bool = Field(default=True)

class TelegramSettings(BaseModel):
    """텔레그램 알림 설정"""
    
    enabled: bool = Field(default=True)
    bot_token: Optional[str] = Field(default=None, description="텔레그램 봇 토큰")
    chat_id: Optional[str] = Field(default=None, description="텔레그램 채팅 ID")
    rate_limit_minutes: int = Field(default=5, ge=1, le=60)
    max_message_length: int = Field(default=4000, ge=100, le=4096)
    
    # 알림 트리거 설정
    notify_on_trade: bool = Field(default=True, description="거래 시 알림")
    notify_on_error: bool = Field(default=True, description="오류 시 알림")
    notify_on_daily_summary: bool = Field(default=True, description="일일 요약 알림")
    
    @validator('bot_token')
    def validate_bot_token_format(cls, v):
        if v and ':' not in v:
            raise ValueError('텔레그램 봇 토큰 형식이 올바르지 않습니다')
        return v
    
    @root_validator
    def validate_telegram_completeness(cls, values):
        enabled = values.get('enabled', True)
        token = values.get('bot_token')
        chat_id = values.get('chat_id')
        
        if enabled and (not token or not chat_id):
            raise ValueError('텔레그램이 활성화되면 bot_token과 chat_id가 모두 필요합니다')
        return values

class MonitoringSettings(BaseModel):
    """모니터링 설정"""
    
    logging: LoggingSettings = LoggingSettings()
    telegram: TelegramSettings = TelegramSettings()
    
    # 성과 추적
    performance_update_interval_minutes: int = Field(default=15, ge=5, le=60)
    daily_summary_time: str = Field(default="09:00", description="일일 요약 시간")
    weekly_report_day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] = Field(default="monday")

class BacktestingSettings(BaseModel):
    """백테스팅 설정"""
    
    start_date: str = Field(default="2023-01-01")
    end_date: str = Field(default="2024-12-31") 
    benchmark: str = Field(default="BTC/USDT")
    slippage_model: Literal["linear", "square_root", "fixed"] = Field(default="linear")
    slippage_bps: int = Field(default=5, ge=0, le=100)
    rebalance_frequency: Literal["hourly", "daily", "weekly"] = Field(default="daily")

class SchedulerSettings(BaseModel):
    """스케줄러 설정"""
    
    timezone: str = Field(default="UTC")
    max_instances: int = Field(default=1, ge=1, le=5)
    misfire_grace_time: int = Field(default=300, ge=60, le=3600, description="지연 허용 시간(초)")

class DashboardSettings(BaseModel):
    """대시보드 설정"""
    
    enabled: bool = Field(default=True)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1024, le=65535)
    refresh_interval_seconds: int = Field(default=30, ge=5, le=300)
    auth_required: bool = Field(default=False)

# =============================================================================
# 메인 설정 클래스 (모든 설정 통합)
# =============================================================================

class ProjectSettings(BaseSettings):
    """Project Odysseus 완전 통합 설정"""
    
    # 프로젝트 메타데이터
    project_name: str = Field(default="Project Odysseus")
    version: str = Field(default="1.0.0")
    core_philosophy: str = Field(default="확률적으로 우위가 확인된, 최적의 시장 환경에서만, 리스크를 통제하며 거래한다")
    
    # 기본 거래 설정
    trading_mode: TradingMode = Field(default=TradingMode.TESTNET, env="TRADING_MODE")
    dry_run: bool = Field(default=True, env="DRY_RUN")
    initial_capital: float = Field(default=1000.0, ge=100.0, le=1000000.0, env="INITIAL_CAPITAL")
    
    # 통합된 세부 설정들
    database: DatabaseSettings = DatabaseSettings()
    exchanges: ExchangeSettings = ExchangeSettings()
    data_collection: DataCollectionSettings = DataCollectionSettings()
    pair_search: PairSearchSettings = PairSearchSettings()
    kalman_filter: KalmanFilterSettings = KalmanFilterSettings()
    market_regime: MarketRegimeSettings = MarketRegimeSettings()
    signal_generation: SignalGenerationSettings = SignalGenerationSettings()
    ml_model: MLModelSettings = MLModelSettings()
    risk_management: RiskManagementSettings = RiskManagementSettings()
    position_sizing: PositionSizingSettings = PositionSizingSettings()
    order_execution: OrderExecutionSettings = OrderExecutionSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    backtesting: BacktestingSettings = BacktestingSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    dashboard: DashboardSettings = DashboardSettings()
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"  # DB__HOST 같은 중첩된 환경 변수 지원
    
    @root_validator
    def validate_overall_consistency(cls, values):
        """전체 설정 일관성 검증"""
        
        # 자본금과 포지션 사이징 일관성
        initial_capital = values.get('initial_capital', 1000)
        position_sizing = values.get('position_sizing', {})
        
        if hasattr(position_sizing, 'min_position_size_usd'):
            min_position = position_sizing.min_position_size_usd
            if initial_capital < min_position * 5:  # 최소 5개 포지션 가능
                raise ValueError(f'초기 자본({initial_capital})이 권장 최소값({min_position * 5}) 미만입니다')
        
        # 라이브 모드 검증
        if values.get('trading_mode') == TradingMode.LIVE:
            exchanges = values.get('exchanges', {})
            if hasattr(exchanges, 'binance_api_key') or hasattr(exchanges, 'bybit_api_key'):
                if not any([
                    exchanges.binance_api_key and exchanges.binance_secret_key,
                    exchanges.bybit_api_key and exchanges.bybit_secret_key
                ]):
                    raise ValueError('라이브 모드에서는 유효한 거래소 API 키가 필요합니다')
        
        return values
    
    def get_summary(self) -> dict:
        """설정 요약 반환"""
        return {
            "project": f"{self.project_name} v{self.version}",
            "mode": f"{self.trading_mode.upper()} ({'DRY-RUN' if self.dry_run else 'LIVE'})",
            "capital": f"${self.initial_capital:,.2f}",
            "primary_exchange": self.exchanges.primary_exchange.upper(),
            "database": f"{self.database.host}:{self.database.port}/{self.database.database}",
            "dashboard": f"http://{self.dashboard.host}:{self.dashboard.port}",
            "telegram_enabled": self.monitoring.telegram.enabled,
            "max_pairs": self.risk_management.position_limits.max_pairs_simultaneous,
            "max_exposure": f"{self.position_sizing.max_total_exposure*100:.1f}%"
        }

# =============================================================================
# 설정 로드 및 검증
# =============================================================================

def load_settings() -> ProjectSettings:
    """설정을 로드하고 검증"""
    try:
        settings = ProjectSettings()
        
        print("✅ 설정 로드 및 검증 완료!")
        
        # 요약 정보 출력
        summary = settings.get_summary()
        print(f"🚀 {summary['project']}")
        print(f"💡 {settings.core_philosophy}")
        print(f"🔧 모드: {summary['mode']}")
        print(f"💰 자본: {summary['capital']}")
        print(f"🏦 거래소: {summary['primary_exchange']}")
        print(f"🌐 대시보드: {summary['dashboard']}")
        
        return settings
        
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. .env 파일의 필수 값들을 확인하세요")
        print("2. 환경 변수 형식이 올바른지 확인하세요")
        print("3. .env.example 파일을 참고하세요")
        raise

# 전역 설정 인스턴스 생성
settings = load_settings()

# =============================================================================
# 편의 함수들
# =============================================================================

def get_db_url() -> str:
    """데이터베이스 연결 URL 생성"""
    return f"postgresql://{settings.database.user}:{settings.database.password}@{settings.database.host}:{settings.database.port}/{settings.database.database}"

def get_exchange_config(exchange: str = None) -> dict:
    """거래소 설정을 ccxt 형식으로 반환"""
    exchange = exchange or settings.exchanges.primary_exchange.value
    
    if exchange == "binance":
        return {
            'apiKey': settings.exchanges.binance_api_key,
            'secret': settings.exchanges.binance_secret_key,
            'testnet': settings.trading_mode == TradingMode.TESTNET,
            'sandbox': settings.trading_mode == TradingMode.TESTNET,
            'enableRateLimit': True,
            'options': {'defaultType': settings.exchanges.market_type.value}
        }
    elif exchange == "bybit":
        return {
            'apiKey': settings.exchanges.bybit_api_key,
            'secret': settings.exchanges.bybit_secret_key,
            'testnet': settings.trading_mode == TradingMode.TESTNET,
            'sandbox': settings.trading_mode == TradingMode.TESTNET,
            'enableRateLimit': True,
            'options': {'defaultType': settings.exchanges.market_type.value}
        }
    else:
        raise ValueError(f"지원하지 않는 거래소: {exchange}")

def is_production() -> bool:
    """운영 환경 여부"""
    return settings.trading_mode == TradingMode.LIVE and not settings.dry_run

# =============================================================================
# 메인 실행부
# =============================================================================

# =============================================================================
# 메인 실행부
# =============================================================================

if __name__ == "__main__":
    print("🔧 Project Odysseus 통합 설정 검증")
    print("=" * 50)
    
    try:
        # 설정 요약 출력
        summary = settings.get_summary()
        
        print("📊 설정 요약:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        print(f"\n🔍 상세 설정 정보:")
        print(f"  페어 탐색: {settings.pair_search.re_search_schedule} 주기")
        print(f"  신호 임계값: Z-score {settings.signal_generation.z_score_entry_threshold}")
        print(f"  리스크 관리: 최대 {settings.risk_management.position_limits.max_pairs_simultaneous}개 페어")
        print(f"  ML 모델: {settings.ml_model.model_type}")
        print(f"  로그 레벨: {settings.monitoring.logging.level}")
        
        # 환경별 권장사항
        if settings.trading_mode == TradingMode.TESTNET:
            print(f"\n💡 테스트넷 모드 체크리스트:")
            print(f"  ✅ 드라이런: {'ON' if settings.dry_run else 'OFF'}")
            print(f"  ✅ API 키: {'설정됨' if settings.exchanges.binance_api_key else '미설정'}")
            print(f"  ✅ 텔레그램: {'활성화' if settings.monitoring.telegram.enabled else '비활성화'}")
        else:
            print(f"\n⚠️  라이브 모드 보안 체크:")
            print(f"  🔒 실제 자금 사용 주의")
            print(f"  🔒 API 키 출금 권한 비활성화 확인")
            print(f"  🔒 포지션 크기 제한 확인")
        
        print(f"\n🎯 다음 단계:")
        print(f"  1. python test_config.py  # 추가 검증")
        print(f"  2. ./docker-scripts.sh start  # Docker 환경 시작")
        print(f"  3. 첫 번째 모듈 개발")
        
    except Exception as e:
        print(f"❌ 설정 검증 중 오류: {e}")
        import traceback
        traceback.print_exc()