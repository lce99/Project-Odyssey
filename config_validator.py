#!/usr/bin/env python3
# config_validator.py - 설정 파일 문법 및 논리 검증기

import ast
import sys
from pathlib import Path
from typing import List, Dict, Any

class ConfigValidator:
    """설정 파일 검증기"""
    
    def __init__(self, config_file: str = "config.py"):
        self.config_file = Path(config_file)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_syntax(self) -> bool:
        """Python 문법 검증"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # AST 파싱으로 문법 검증
            ast.parse(source, filename=str(self.config_file))
            print("✅ Python 문법 검증 통과")
            return True
            
        except SyntaxError as e:
            self.errors.append(f"문법 오류 (라인 {e.lineno}): {e.msg}")
            print(f"❌ Python 문법 오류: {e}")
            return False
        except Exception as e:
            self.errors.append(f"파일 읽기 오류: {e}")
            return False
    
    def validate_imports(self) -> bool:
        """Import 검증"""
        try:
            # config.py를 임포트하여 실행 시 오류 확인
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", self.config_file)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                print("✅ 모듈 임포트 검증 통과")
                return True
        except ImportError as e:
            self.errors.append(f"임포트 오류: {e}")
            print(f"❌ 임포트 오류: {e}")
            return False
        except Exception as e:
            self.errors.append(f"모듈 실행 오류: {e}")
            print(f"❌ 모듈 실행 오류: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """설정 구조 검증"""
        required_configs = [
            'PROJECT_NAME',
            'VERSION', 
            'DB_CONFIG',
            'EXCHANGE_CONFIG',
            'TRADING_MODE',
            'INITIAL_CAPITAL_USD',
            'RISK_MANAGEMENT_CONFIG',
            'MONITOR_CONFIG'
        ]
        
        try:
            import config as config
            
            missing_configs = []
            for required in required_configs:
                if not hasattr(config, required):
                    missing_configs.append(required)
            
            if missing_configs:
                self.errors.extend([f"필수 설정 누락: {cfg}" for cfg in missing_configs])
                return False
            
            print("✅ 설정 구조 검증 통과")
            return True
            
        except Exception as e:
            self.errors.append(f"구조 검증 실패: {e}")
            return False
    
    def validate_data_types(self) -> bool:
        """데이터 타입 검증"""
        try:
            import config as config
            
            # 타입 검증 규칙
            type_rules = {
                'PROJECT_NAME': str,
                'VERSION': str,
                'INITIAL_CAPITAL_USD': (int, float),
                'DRY_RUN': bool,
                'DB_CONFIG': dict,
                'EXCHANGE_CONFIG': dict,
                'RISK_MANAGEMENT_CONFIG': dict
            }
            
            type_errors = []
            for attr_name, expected_type in type_rules.items():
                if hasattr(config, attr_name):
                    actual_value = getattr(config, attr_name)
                    if not isinstance(actual_value, expected_type):
                        type_errors.append(
                            f"{attr_name}: 예상 타입 {expected_type}, 실제 타입 {type(actual_value)}"
                        )
            
            if type_errors:
                self.errors.extend(type_errors)
                return False
            
            print("✅ 데이터 타입 검증 통과")
            return True
            
        except Exception as e:
            self.errors.append(f"타입 검증 실패: {e}")
            return False
    
    def validate_config_values(self) -> bool:
        """설정값 논리 검증"""
        try:
            import config as config
            
            # 논리적 검증 규칙들
            validations = []
            
            # 1. 자본금 검증
            if hasattr(config, 'INITIAL_CAPITAL_USD'):
                if config.INITIAL_CAPITAL_USD <= 0:
                    validations.append("INITIAL_CAPITAL_USD는 0보다 커야 합니다")
                elif config.INITIAL_CAPITAL_USD < 100:
                    self.warnings.append("INITIAL_CAPITAL_USD가 $100 미만입니다 (권장: $100 이상)")
            
            # 2. 리스크 관리 설정 검증
            if hasattr(config, 'RISK_MANAGEMENT_CONFIG'):
                risk_config = config.RISK_MANAGEMENT_CONFIG
                
                # 손절매 임계값 검증
                if 'stop_loss' in risk_config:
                    stop_loss = risk_config['stop_loss']
                    if 'z_score_threshold' in stop_loss:
                        threshold = stop_loss['z_score_threshold']
                        if threshold <= 1.5:
                            validations.append("Z-score 손절매 임계값이 너무 낮습니다 (권장: 2.0 이상)")
                        elif threshold > 5.0:
                            self.warnings.append("Z-score 손절매 임계값이 매우 높습니다")
                
                # 포지션 제한 검증
                if 'position_limits' in risk_config:
                    pos_limits = risk_config['position_limits']
                    if 'max_pairs_simultaneous' in pos_limits:
                        max_pairs = pos_limits['max_pairs_simultaneous']
                        if max_pairs <= 0:
                            validations.append("동시 보유 최대 페어 수는 1 이상이어야 합니다")
                        elif max_pairs > 20:
                            self.warnings.append("동시 보유 페어 수가 많습니다 (관리 복잡성 증가)")
            
            # 3. 포지션 사이징 일관성 검증
            if hasattr(config, 'POSITION_SIZING_CONFIG'):
                pos_config = config.POSITION_SIZING_CONFIG
                max_per_pair = pos_config.get('max_position_per_pair', 0)
                max_total = pos_config.get('max_total_exposure', 0)
                
                if max_per_pair > max_total:
                    validations.append(
                        "페어당 최대 포지션이 전체 최대 노출보다 클 수 없습니다"
                    )
            
            if validations:
                self.errors.extend(validations)
                return False
            
            print("✅ 설정값 논리 검증 통과")
            return True
            
        except Exception as e:
            self.errors.append(f"설정값 검증 실패: {e}")
            return False
    
    def run_full_validation(self) -> bool:
        """전체 검증 실행"""
        print("🔧 Config 파일 전체 검증 시작...")
        print("=" * 50)
        
        validations = [
            ("문법 검증", self.validate_syntax),
            ("임포트 검증", self.validate_imports), 
            ("구조 검증", self.validate_structure),
            ("타입 검증", self.validate_data_types),
            ("논리 검증", self.validate_config_values)
        ]
        
        all_passed = True
        
        for name, validator in validations:
            print(f"\n📋 {name} 중...")
            try:
                if not validator():
                    all_passed = False
                    print(f"❌ {name} 실패")
                else:
                    print(f"✅ {name} 성공")
            except Exception as e:
                self.errors.append(f"{name} 중 예외 발생: {e}")
                all_passed = False
                print(f"❌ {name} 예외: {e}")
        
        # 결과 요약
        print("\n" + "=" * 50)
        
        if all_passed:
            print("🎉 모든 검증 통과!")
            
            if self.warnings:
                print(f"\n⚠️  경고사항 ({len(self.warnings)}개):")
                for warning in self.warnings:
                    print(f"  - {warning}")
        else:
            print(f"❌ 검증 실패 ({len(self.errors)}개 오류)")
            print("\n🐛 발견된 오류들:")
            for error in self.errors:
                print(f"  - {error}")
        
        return all_passed
    
    def suggest_fixes(self) -> None:
        """수정 제안"""
        if not self.errors:
            return
        
        print(f"\n💡 수정 제안:")
        
        for error in self.errors:
            if "문법 오류" in error:
                print("  🔧 Python 문법을 확인하세요 (괄호, 따옴표, 들여쓰기)")
            elif "필수 설정 누락" in error:
                print("  🔧 누락된 설정을 추가하거나 .env 파일을 확인하세요")
            elif "타입" in error:
                print("  🔧 변수의 데이터 타입을 확인하세요")
            elif "임포트 오류" in error:
                print("  🔧 requirements.txt의 패키지들이 설치되어 있는지 확인하세요")
        
        print("\n📖 추가 도움말:")
        print("  - .env.example 파일을 참고하여 .env 파일을 작성하세요")
        print("  - python -m py_compile config.py 명령으로도 문법을 확인할 수 있습니다")
        print("  - IDE에서 타입 힌트를 활용하면 오류를 미리 발견할 수 있습니다")

def main():
    """메인 실행 함수"""
    validator = ConfigValidator()
    
    if not validator.config_file.exists():
        print(f"❌ 설정 파일을 찾을 수 없습니다: {validator.config_file}")
        sys.exit(1)
    
    success = validator.run_full_validation()
    
    if not success:
        validator.suggest_fixes()
        sys.exit(1)
    else:
        print(f"\n🎯 설정 파일 '{validator.config_file}'이 모든 검증을 통과했습니다!")
        
        # Pydantic 검증도 실행 권장
        print(f"\n💡 추가 권장사항:")
        print(f"  python config.py  # Pydantic 기반 상세 검증 실행")

if __name__ == "__main__":
    main()