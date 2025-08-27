# data_module.py - Project Odysseus 데이터 수집 및 관리 모듈
# 동적 적응형 페어 트레이딩 봇의 핵심 데이터 파이프라인

import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import ccxt
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from loguru import logger
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Project Odysseus 설정 import
from config import settings, get_db_url, get_exchange_config

# =============================================================================
# 1. 데이터 모델 및 열거형
# =============================================================================

class DataStatus(Enum):
    """데이터 상태"""
    VALID = "valid"
    INTERPOLATED = "interpolated" 
    MISSING = "missing"
    CORRUPTED = "corrupted"

class DataSource(Enum):
    """데이터 소스"""
    API = "api"
    WEBSOCKET = "websocket"
    MANUAL = "manual"
    INTERPOLATION = "interpolation"

@dataclass
class MarketData:
    """시장 데이터 구조체"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None
    trades_count: Optional[int] = None
    taker_buy_volume: Optional[float] = None
    taker_buy_quote_volume: Optional[float] = None
    data_source: DataSource = DataSource.API
    is_interpolated: bool = False
    
    def __post_init__(self):
        """데이터 검증"""
        if not all([self.open > 0, self.high > 0, self.low > 0, self.close > 0]):
            raise ValueError(f"Invalid OHLC data for {self.symbol}: O={self.open}, H={self.high}, L={self.low}, C={self.close}")
        
        if not (self.high >= max(self.open, self.close) and self.low <= min(self.open, self.close)):
            raise ValueError(f"OHLC logic violation for {self.symbol}")
        
        if self.volume < 0:
            raise ValueError(f"Negative volume for {self.symbol}: {self.volume}")

@dataclass
class DataQualityMetrics:
    """데이터 품질 메트릭"""
    symbol: str
    total_records: int
    missing_records: int
    interpolated_records: int
    corrupted_records: int
    quality_score: float
    last_update: datetime
    
    @property
    def missing_ratio(self) -> float:
        return self.missing_records / max(self.total_records, 1)
    
    @property
    def is_healthy(self) -> bool:
        return self.quality_score >= 0.95 and self.missing_ratio <= 0.05

# =============================================================================
# 2. 데이터베이스 연결 관리자
# =============================================================================

class DatabaseManager:
    """데이터베이스 연결 및 작업 관리"""
    
    def __init__(self):
        self.db_url = get_db_url()
        self.engine = create_engine(
            self.db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600  # 1시간마다 연결 재생성
        )
        self.connection = None
        
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.connection = self.engine.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self.connection:
            self.connection.close()
    
    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: Dict = None) -> Any:
        """쿼리 실행"""
        try:
            if self.connection:
                return self.connection.execute(text(query), params or {})
            else:
                with self.engine.connect() as conn:
                    return conn.execute(text(query), params or {})
        except SQLAlchemyError as e:
            logger.error(f"Database query failed: {query[:100]}... Error: {e}")
            raise
    
    def insert_market_data(self, data_list: List[MarketData]) -> int:
        """시장 데이터 대량 삽입"""
        if not data_list:
            return 0
        
        insert_query = """
            INSERT INTO market_data.price_data 
            (time, symbol, exchange, timeframe, open, high, low, close, volume,
             quote_volume, trades_count, taker_buy_volume, taker_buy_quote_volume,
             is_interpolated, data_source, created_at)
            VALUES 
            (%(timestamp)s, %(symbol)s, %(exchange)s, %(timeframe)s, 
             %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s,
             %(quote_volume)s, %(trades_count)s, %(taker_buy_volume)s, %(taker_buy_quote_volume)s,
             %(is_interpolated)s, %(data_source)s, NOW())
            ON CONFLICT (time, symbol, exchange, timeframe) 
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high, 
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                quote_volume = EXCLUDED.quote_volume,
                is_interpolated = EXCLUDED.is_interpolated,
                data_source = EXCLUDED.data_source
        """
        
        records = []
        for data in data_list:
            records.append({
                'timestamp': data.timestamp,
                'symbol': data.symbol,
                'exchange': 'binance',  # 현재는 바이낸스만 지원
                'timeframe': data.timeframe,
                'open': data.open,
                'high': data.high,
                'low': data.low,
                'close': data.close,
                'volume': data.volume,
                'quote_volume': data.quote_volume,
                'trades_count': data.trades_count,
                'taker_buy_volume': data.taker_buy_volume,
                'taker_buy_quote_volume': data.taker_buy_quote_volume,
                'is_interpolated': data.is_interpolated,
                'data_source': data.data_source.value
            })
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(insert_query), records)
                conn.commit()
                return len(records)
        except SQLAlchemyError as e:
            logger.error(f"Failed to insert market data: {e}")
            raise

# =============================================================================
# 3. 거래소 API 클라이언트
# =============================================================================

class ExchangeAPIManager:
    """거래소 API 통신 관리자"""
    
    def __init__(self):
        self.exchange_config = get_exchange_config()
        self.exchange = self._initialize_exchange()
        self.session = self._create_session()
        
        # 재시도 설정 (지수 백오프)
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        
    def _initialize_exchange(self) -> ccxt.Exchange:
        """거래소 클라이언트 초기화"""
        try:
            exchange_class = getattr(ccxt, settings.exchanges.primary_exchange.value)
            exchange = exchange_class(self.exchange_config)
            
            # API 연결 테스트
            exchange.load_markets()
            logger.info(f"✅ {settings.exchanges.primary_exchange.value} API initialized successfully")
            
            return exchange
        except Exception as e:
            logger.error(f"❌ Failed to initialize exchange API: {e}")
            raise
    
    def _create_session(self) -> requests.Session:
        """HTTP 세션 생성 (재시도 정책 포함)"""
        session = requests.Session()
        
        # 재시도 전략 설정
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    async def fetch_ohlcv_with_retry(
        self, 
        symbol: str, 
        timeframe: str, 
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """OHLCV 데이터 조회 (재시도 로직 포함)"""
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching OHLCV for {symbol} {timeframe}, attempt {attempt + 1}")
                
                # ccxt를 통한 데이터 조회
                ohlcv_data = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit
                )
                
                if not ohlcv_data:
                    raise ValueError(f"No data returned for {symbol} {timeframe}")
                
                logger.debug(f"✅ Successfully fetched {len(ohlcv_data)} records for {symbol}")
                return ohlcv_data
                
            except ccxt.NetworkError as e:
                logger.warning(f"🌐 Network error for {symbol} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Network error persists after {self.max_retries} attempts")
                    raise
                    
            except ccxt.ExchangeError as e:
                # API 한도 초과 등의 거래소 오류
                if "rate limit" in str(e).lower():
                    logger.warning(f"⏱️ Rate limit hit for {symbol}, waiting...")
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ Exchange error for {symbol}: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error fetching {symbol}: {e}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        # 모든 재시도 실패
        raise Exception(f"Failed to fetch {symbol} {timeframe} after {self.max_retries} attempts")
    
    def convert_ohlcv_to_market_data(
        self, 
        ohlcv_list: List[List], 
        symbol: str, 
        timeframe: str
    ) -> List[MarketData]:
        """OHLCV 원시 데이터를 MarketData 객체로 변환"""
        market_data_list = []
        
        for ohlcv in ohlcv_list:
            try:
                # ccxt OHLCV 형식: [timestamp, open, high, low, close, volume]
                timestamp = datetime.fromtimestamp(ohlcv[0] / 1000)  # ms to seconds
                
                market_data = MarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=float(ohlcv[1]),
                    high=float(ohlcv[2]),
                    low=float(ohlcv[3]),
                    close=float(ohlcv[4]),
                    volume=float(ohlcv[5]),
                    data_source=DataSource.API
                )
                
                market_data_list.append(market_data)
                
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Invalid OHLCV data for {symbol}: {ohlcv}, Error: {e}")
                continue
        
        return market_data_list

# =============================================================================
# 4. 데이터 검증 및 품질 관리자
# =============================================================================

class DataValidator:
    """데이터 검증 및 품질 관리"""
    
    def __init__(self):
        self.validation_policy = settings.data_collection.validation_policy
        self.max_interpolation_gap = 5  # 최대 5개까지만 보간
        
    def validate_data_integrity(self, data_list: List[MarketData]) -> Tuple[List[MarketData], DataQualityMetrics]:
        """데이터 무결성 검증 및 품질 메트릭 계산"""
        
        if not data_list:
            return [], DataQualityMetrics(
                symbol="unknown",
                total_records=0,
                missing_records=0,
                interpolated_records=0,
                corrupted_records=0,
                quality_score=0.0,
                last_update=datetime.now()
            )
        
        symbol = data_list[0].symbol
        original_count = len(data_list)
        validated_data = []
        corrupted_count = 0
        
        # 1. 기본 데이터 검증
        for data in data_list:
            try:
                # MarketData 자체 검증 (__post_init__)이 실행됨
                validated_data.append(data)
            except ValueError as e:
                logger.warning(f"⚠️ Corrupted data detected for {symbol}: {e}")
                corrupted_count += 1
        
        # 2. 시간 순서 정렬
        validated_data.sort(key=lambda x: x.timestamp)
        
        # 3. 누락 데이터 탐지 및 보간
        interpolated_data, interpolated_count = self._handle_missing_data(validated_data)
        
        # 4. 품질 점수 계산
        quality_score = self._calculate_quality_score(
            total=original_count,
            corrupted=corrupted_count,
            interpolated=interpolated_count
        )
        
        # 5. 품질 메트릭 생성
        quality_metrics = DataQualityMetrics(
            symbol=symbol,
            total_records=len(interpolated_data),
            missing_records=max(0, original_count - len(validated_data)),
            interpolated_records=interpolated_count,
            corrupted_records=corrupted_count,
            quality_score=quality_score,
            last_update=datetime.now()
        )
        
        logger.info(f"📊 Data validation completed for {symbol}: "
                   f"Quality={quality_score:.3f}, "
                   f"Total={len(interpolated_data)}, "
                   f"Interpolated={interpolated_count}, "
                   f"Corrupted={corrupted_count}")
        
        return interpolated_data, quality_metrics
    
    def _handle_missing_data(self, data_list: List[MarketData]) -> Tuple[List[MarketData], int]:
        """누락 데이터 처리 (보간 또는 제외)"""
        
        if len(data_list) < 2:
            return data_list, 0
        
        # 시간 간격 계산 (timeframe 기준)
        timeframe = data_list[0].timeframe
        expected_interval = self._get_timeframe_minutes(timeframe)
        
        filled_data = []
        interpolated_count = 0
        
        for i in range(len(data_list)):
            filled_data.append(data_list[i])
            
            # 다음 데이터와의 시간 간격 확인
            if i < len(data_list) - 1:
                current_time = data_list[i].timestamp
                next_time = data_list[i + 1].timestamp
                time_diff_minutes = (next_time - current_time).total_seconds() / 60
                
                expected_gaps = int(time_diff_minutes / expected_interval) - 1
                
                # 누락된 데이터가 있고, 보간 가능한 범위 내인 경우
                if expected_gaps > 0 and expected_gaps <= self.max_interpolation_gap:
                    if self.validation_policy == settings.data_collection.DataValidationPolicy.INTERPOLATE:
                        interpolated_points = self._interpolate_data(
                            data_list[i], 
                            data_list[i + 1], 
                            expected_gaps
                        )
                        filled_data.extend(interpolated_points)
                        interpolated_count += len(interpolated_points)
                        
                        logger.debug(f"🔧 Interpolated {len(interpolated_points)} points between "
                                   f"{current_time} and {next_time} for {data_list[i].symbol}")
                
                elif expected_gaps > self.max_interpolation_gap:
                    # 너무 큰 간격은 심각한 문제로 간주
                    logger.error(f"❌ Large data gap detected for {data_list[i].symbol}: "
                               f"{expected_gaps} missing intervals between {current_time} and {next_time}")
        
        return filled_data, interpolated_count
    
    def _interpolate_data(self, start_data: MarketData, end_data: MarketData, gap_count: int) -> List[MarketData]:
        """선형 보간으로 누락 데이터 생성"""
        interpolated = []
        
        # 시간 간격 계산
        time_delta = (end_data.timestamp - start_data.timestamp) / (gap_count + 1)
        
        for i in range(1, gap_count + 1):
            # 선형 보간 비율
            ratio = i / (gap_count + 1)
            
            interpolated_timestamp = start_data.timestamp + (time_delta * i)
            
            # OHLC 데이터 선형 보간
            interpolated_data = MarketData(
                symbol=start_data.symbol,
                timeframe=start_data.timeframe,
                timestamp=interpolated_timestamp,
                open=start_data.close + (end_data.open - start_data.close) * ratio,
                high=max(start_data.close, end_data.open) + abs(start_data.high - end_data.high) * ratio,
                low=min(start_data.close, end_data.open) - abs(start_data.low - end_data.low) * ratio,
                close=start_data.close + (end_data.close - start_data.close) * ratio,
                volume=start_data.volume + (end_data.volume - start_data.volume) * ratio,
                data_source=DataSource.INTERPOLATION,
                is_interpolated=True
            )
            
            interpolated.append(interpolated_data)
        
        return interpolated
    
    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """timeframe 문자열을 분 단위로 변환"""
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '6h': 360,
            '12h': 720,
            '1d': 1440
        }
        return timeframe_minutes.get(timeframe, 60)  # 기본값: 1시간
    
    def _calculate_quality_score(self, total: int, corrupted: int, interpolated: int) -> float:
        """데이터 품질 점수 계산 (0.0 ~ 1.0)"""
        if total == 0:
            return 0.0
        
        # 가중치: 손상된 데이터는 보간된 데이터보다 더 심각한 문제
        corruption_penalty = (corrupted * 0.5) / total
        interpolation_penalty = (interpolated * 0.2) / total
        
        quality_score = max(0.0, 1.0 - corruption_penalty - interpolation_penalty)
        return min(1.0, quality_score)

# =============================================================================
# 5. 메인 데이터 핸들러 클래스
# =============================================================================

class DataHandler:
    """Project Odysseus 메인 데이터 수집 및 관리 클래스"""
    
    def __init__(self):
        """데이터 핸들러 초기화"""
        # 컴포넌트 초기화
        self.db_manager = DatabaseManager()
        self.api_manager = ExchangeAPIManager()
        self.validator = DataValidator()
        
        # 설정값 로드
        self.target_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT']
        self.primary_timeframe = '1h'
        self.collection_interval = 60  # 개발 단계: 60초
        
        # 품질 메트릭 추적
        self.quality_metrics: Dict[str, DataQualityMetrics] = {}
        
        # 실행 상태
        self.is_running = False
        self.last_collection_time = None
        
        logger.info("🚀 DataHandler initialized successfully")
        logger.info(f"📊 Target symbols: {self.target_symbols}")
        logger.info(f"⏱️ Collection interval: {self.collection_interval}s")
        logger.info(f"🕐 Primary timeframe: {self.primary_timeframe}")
    
    def test_connections(self) -> bool:
        """모든 연결 테스트"""
        logger.info("🔍 Testing all connections...")
        
        # 데이터베이스 연결 테스트
        if not self.db_manager.test_connection():
            logger.error("❌ Database connection failed")
            return False
        logger.info("✅ Database connection OK")
        
        # 거래소 API 테스트
        try:
            markets = self.api_manager.exchange.load_markets()
            if not markets:
                logger.error("❌ Exchange API test failed: No markets loaded")
                return False
            logger.info(f"✅ Exchange API OK ({len(markets)} markets loaded)")
        except Exception as e:
            logger.error(f"❌ Exchange API test failed: {e}")
            return False
        
        return True
    
    async def fetch_historical_data(
        self, 
        symbol: str, 
        timeframe: str = None,
        days_back: int = 30
    ) -> List[MarketData]:
        """과거 데이터 수집"""
        
        timeframe = timeframe or self.primary_timeframe
        since_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
        
        logger.info(f"📚 Fetching historical data for {symbol} {timeframe} "
                   f"(last {days_back} days)")
        
        try:
            # API에서 데이터 조회
            ohlcv_data = await self.api_manager.fetch_ohlcv_with_retry(
                symbol=symbol,
                timeframe=timeframe,
                since=since_timestamp,
                limit=1000  # 대부분 거래소의 최대 제한
            )
            
            # MarketData 객체로 변환
            market_data_list = self.api_manager.convert_ohlcv_to_market_data(
                ohlcv_data, symbol, timeframe
            )
            
            # 데이터 검증 및 품질 관리
            validated_data, quality_metrics = self.validator.validate_data_integrity(market_data_list)
            self.quality_metrics[symbol] = quality_metrics
            
            logger.info(f"✅ Historical data collected for {symbol}: "
                       f"{len(validated_data)} records, quality={quality_metrics.quality_score:.3f}")
            
            return validated_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch historical data for {symbol}: {e}")
            raise
    
    async def fetch_realtime_data(self, symbol: str, timeframe: str = None) -> List[MarketData]:
        """실시간 데이터 수집 (최신 몇 개 캔들)"""
        
        timeframe = timeframe or self.primary_timeframe
        
        try:
            # 최근 5개 캔들 조회 (확실한 완료된 캔들을 위해)
            ohlcv_data = await self.api_manager.fetch_ohlcv_with_retry(
                symbol=symbol,
                timeframe=timeframe,
                limit=5
            )
            
            # MarketData 객체로 변환
            market_data_list = self.api_manager.convert_ohlcv_to_market_data(
                ohlcv_data, symbol, timeframe
            )
            
            # 최신 데이터만 반환 (마지막 캔들은 미완료일 수 있으므로 제외)
            if len(market_data_list) > 1:
                return market_data_list[:-1]  # 마지막 캔들 제외
            else:
                return market_data_list
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch realtime data for {symbol}: {e}")
            return []
    
    def get_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        timeframe: str = None
    ) -> pd.DataFrame:
        """데이터베이스에서 특정 기간의 데이터 조회"""
        
        timeframe = timeframe or self.primary_timeframe
        
        query = """
            SELECT 
                time, symbol, timeframe, open, high, low, close, volume,
                quote_volume, is_interpolated, data_source, created_at
            FROM market_data.price_data
            WHERE symbol = %(symbol)s 
                AND timeframe = %(timeframe)s
                AND time BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY time ASC
        """
        
        params = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            with self.db_manager as db:
                result = db.execute_query(query, params)
                df = pd.DataFrame(result.fetchall())
                
                if not df.empty:
                    df.set_index('time', inplace=True)
                    logger.info(f"📊 Retrieved {len(df)} records for {symbol} {timeframe}")
                else:
                    logger.warning(f"⚠️ No data found for {symbol} {timeframe} in specified period")
                
                return df
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def collect_and_store_data(self, symbols: List[str] = None) -> Dict[str, int]:
        """데이터 수집 및 저장 (메인 작업 함수)"""
        
        symbols = symbols or self.target_symbols
        results = {}
        
        logger.info(f"🔄 Starting data collection for {len(symbols)} symbols...")
        
        for symbol in symbols:
            try:
                # 실시간 데이터 수집
                market_data_list = await self.fetch_realtime_data(symbol)
                
                if market_data_list:
                    # 데이터 검증
                    validated_data, quality_metrics = self.validator.validate_data_integrity(market_data_list)
                    self.quality_metrics[symbol] = quality_metrics
                    
                    # 데이터베이스에 저장
                    with self.db_manager as db:
                        inserted_count = db.insert_market_data(validated_data)
                        results[symbol] = inserted_count
                        
                        logger.info(f"💾 Stored {inserted_count} records for {symbol} "
                                   f"(Quality: {quality_metrics.quality_score:.3f})")
                else:
                    results[symbol] = 0
                    logger.warning(f"⚠️ No new data for {symbol}")
                
            except Exception as e:
                logger.error(f"❌ Data collection failed for {symbol}: {e}")
                results[symbol] = -1  # 오류 표시