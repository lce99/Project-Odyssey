# 🔐 Project Odysseus 보안 가이드

## 📋 보안 체크리스트

### ✅ 필수 보안 설정

#### 1. 환경 변수 관리
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] `.env.example`이나 `.env.template`에는 실제 값을 넣지 않음
- [ ] 모든 민감 정보는 환경 변수로만 관리

#### 2. 거래소 API 보안
- [ ] **출금 권한 절대 부여 금지** - Spot & Margin Trading, Futures Trading만 허용
- [ ] IP 화이트리스트 설정 (고정 IP 사용 권장)
- [ ] API 키 정기 재생성 (월 1회 권장)
- [ ] 테스트넷과 라이브 환경 API 키 분리

#### 3. 데이터베이스 보안
- [ ] 강력한 패스워드 사용 (16자 이상, 특수문자 포함)
- [ ] 데이터베이스 접근을 특정 IP로 제한
- [ ] SSL/TLS 연결 사용 (프로덕션 환경)
- [ ] 정기적인 백업 및 암호화

#### 4. 서버/인프라 보안
- [ ] 방화벽 설정 (필요한 포트만 개방)
- [ ] SSH 키 기반 인증 (패스워드 인증 비활성화)
- [ ] 시스템 업데이트 자동화
- [ ] 모니터링 및 로깅 설정

## 🚨 보안 위협 시나리오 및 대응

### 1. API 키 노출 시 대응
```bash
# 즉시 실행할 명령들:
1. 거래소에서 해당 API 키 즉시 비활성화
2. 새로운 API 키 생성 및 .env 파일 업데이트
3. 최근 거래 내역 확인
4. 이상 거래 발견시 거래소 고객센터 연락
```

### 2. 서버 침입 의심 시 대응
```bash
# 점검 사항:
1. 시스템 로그 확인: /var/log/auth.log
2. 네트워크 연결 확인: netstat -tulpn
3. 실행 중인 프로세스 확인: ps aux
4. 파일 변경 확인: find /path -type f -mtime -1
5. 봇 즉시 중단 후 점검 완료까지 거래 금지
```

### 3. 데이터베이스 보안 점검
```sql
-- 접근 로그 확인
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- 권한 확인
SELECT * FROM information_schema.role_table_grants 
WHERE grantee = 'your_user';

-- 의심스러운 쿼리 확인
SELECT query, state, client_addr 
FROM pg_stat_activity 
WHERE query NOT LIKE '%pg_stat_activity%';
```

## 🛡️ 보안 모범 사례

### 개발 환경
```bash
# 1. 전용 테스트넷 계정 사용
# 2. 실제 자금 없는 환경에서 테스트
# 3. 로컬 개발 시에도 HTTPS 사용 권장
# 4. Git hook으로 민감 정보 커밋 방지

# Git hook 설정 예시 (.git/hooks/pre-commit):
#!/bin/bash
if git diff --cached --name-only | grep -q "\.env$"; then
    echo "❌ .env 파일을 커밋하려고 합니다!"
    exit 1
fi
```

### 프로덕션 환경
```bash
# 1. 전용 서버 사용 (VPS 또는 클라우드)
# 2. VPN 또는 전용선 연결
# 3. 정기적인 보안 점검 자동화
# 4. 이중 인증(2FA) 모든 서비스에 적용
# 5. 접근 로그 모니터링 및 알림
```

### API 키 권한 설정 (Binance 예시)
```
✅ 허용할 권한:
- Enable Reading
- Enable Spot & Margin Trading
- Enable Futures Trading (필요시)

❌ 절대 허용 금지:
- Enable Withdrawals
- Enable Internal Transfer
- Permits Universal Transfer
```

### 네트워크 보안 설정
```bash
# 방화벽 설정 (Ubuntu/Debian)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5432/tcp  # PostgreSQL (내부 네트워크만)
sudo ufw allow 8000/tcp  # 대시보드 (필요시)
sudo ufw deny 80/tcp     # 불필요한 포트 차단
sudo ufw deny 443/tcp    # 불필요한 포트 차단
```

## 🔍 보안 모니터링

### 자동 모니터링 설정
```python
# monitoring_module.py에 추가할 보안 체크 로직
def security_health_check():
    checks = [
        check_api_key_validity(),
        check_database_connections(), 
        check_suspicious_activities(),
        check_system_resources(),
        check_recent_trades()
    ]
    return all(checks)

def check_suspicious_activities():
    # 1. 예상치 못한 대량 거래
    # 2. 비정상적인 수익률 변화
    # 3. API 호출 실패율 급증
    # 4. 데이터베이스 접근 패턴 이상
    pass
```

### 알림 설정
```python
# 즉시 알림이 필요한 보안 이벤트들
CRITICAL_SECURITY_EVENTS = [
    'api_key_error',           # API 키 오류
    'unauthorized_access',     # 비인가 접근 시도
    'unusual_trading_volume',  # 비정상적 거래량
    'database_connection_fail', # DB 연결 실패
    'system_resource_critical' # 시스템 리소스 부족
]
```

## 📚 추가 보안 리소스

### 참고 문서
- [Binance API 보안 가이드](https://binance-docs.github.io/apidocs/spot/en/#general-info)
- [PostgreSQL 보안 체크리스트](https://www.postgresql.org/docs/current/security-checklist.html)
- [Python 보안 모범사례](https://python.org/dev/security/)

### 보안 도구
- **Fail2ban**: 무차별 대입 공격 방지
- **AIDE**: 파일 무결성 모니터링  
- **Lynis**: 시스템 보안 감사
- **Nmap**: 네트워크 포트 스캔

### 정기 점검 일정
- **일간**: 거래 로그 및 시스템 상태 확인
- **주간**: 보안 이벤트 로그 분석
- **월간**: API 키 재생성 및 권한 점검
- **분기**: 전체 시스템 보안 감사

## 🆘 비상 연락처

```
보안 사고 발생시:
1. 봇 즉시 중단: pkill -f main.py
2. 네트워크 차단: sudo ufw deny out 443
3. 거래소 API 비활성화
4. 로그 백업 및 분석
5. 전문가 상담 (필요시)
```

---
**⚠️ 중요**: 이 보안 가이드는 참고용입니다. 실제 프로덕션 환경에서는 보안 전문가의 검토를 받으시기 바랍니다.