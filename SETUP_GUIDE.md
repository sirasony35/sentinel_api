# Sentinel Hub 설정 가이드

이 문서는 Sentinel Hub API를 사용하기 위한 계정 설정 및 자격 증명 발급 과정을 안내합니다.

## 1단계: Sentinel Hub 계정 생성

### 1.1 회원가입
1. [Sentinel Hub 웹사이트](https://www.sentinel-hub.com/)에 접속
2. 우측 상단의 "Sign Up" 클릭
3. 이메일 주소와 비밀번호로 계정 생성
4. 이메일 인증 완료

### 1.2 무료 플랜 선택
- Trial 계정은 매달 무료 프로세싱 유닛 제공
- 개발 및 테스트 목적으로 충분

## 2단계: OAuth Client 생성

### 2.1 Dashboard 접속
1. [Sentinel Hub Dashboard](https://apps.sentinel-hub.com/dashboard/) 로그인
2. 좌측 메뉴에서 "User Settings" 선택

### 2.2 OAuth Client 생성
1. "OAuth clients" 탭 클릭
2. "+ Create new" 버튼 클릭
3. Client 정보 입력:
   - **Name**: 프로젝트 이름 (예: "My Sentinel Project")
   - **Description**: 간단한 설명 (선택사항)
   - **Redirect URIs**: 비워두거나 `http://localhost` 입력
4. "Create client" 버튼 클릭

### 2.3 자격 증명 확인
생성된 OAuth Client에서 다음 정보를 확인하고 안전하게 보관:
- **Client ID**: 공개 식별자
- **Client Secret**: 비밀 키 (절대 공유 금지!)

## 3단계: 프로젝트 설정

### 3.1 설정 파일 생성

프로젝트 루트 디렉토리에서:

```bash
cp config_example.py config.py
```

### 3.2 자격 증명 입력

`config.py` 파일을 열고 발급받은 정보 입력:

```python
# config.py
SENTINEL_HUB_CLIENT_ID = "abcd1234-5678-90ef-ghij-klmnopqrstuv"
SENTINEL_HUB_CLIENT_SECRET = "ABcdEF12ghIJ34klMN56opQR78stUV90wxYZ"
```

⚠️ **보안 주의사항:**
- `config.py` 파일은 절대 Git에 커밋하지 마세요
- `.gitignore`에 이미 추가되어 있습니다
- 자격 증명을 코드에 직접 작성하지 마세요

### 3.3 환경 변수 사용 (선택사항)

더 안전한 방법으로 환경 변수를 사용할 수 있습니다:

```bash
# Linux/Mac
export SENTINEL_HUB_CLIENT_ID="your_client_id"
export SENTINEL_HUB_CLIENT_SECRET="your_client_secret"

# Windows
set SENTINEL_HUB_CLIENT_ID=your_client_id
set SENTINEL_HUB_CLIENT_SECRET=your_client_secret
```

Python 코드에서:

```python
import os

CLIENT_ID = os.getenv('SENTINEL_HUB_CLIENT_ID')
CLIENT_SECRET = os.getenv('SENTINEL_HUB_CLIENT_SECRET')
```

## 4단계: 설치 및 테스트

### 4.1 의존성 설치

```bash
pip install -r requirements.txt
```

### 4.2 간단한 테스트

```python
from old.sentinel_downloader import SentinelDownloader

# 자격 증명으로 초기화 (오류가 없으면 성공)
downloader = SentinelDownloader(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

print("✓ Sentinel Hub 연결 성공!")
```

### 4.3 예제 실행

```bash
# 간단한 예제
python example_simple.py

# 고급 예제
python example_advanced.py
```

## 5단계: API 사용량 확인

### 5.1 Dashboard에서 모니터링
1. [Dashboard](https://apps.sentinel-hub.com/dashboard/) 접속
2. "Account" → "Statistics" 메뉴
3. Processing Units (PU) 사용량 확인

### 5.2 사용량 최적화 팁
- 필요한 지역만 다운로드 (BBox를 작게 설정)
- 적절한 해상도 선택 (10m보다 20m가 처리량 적음)
- 시간 범위를 좁게 설정
- 구름 커버 필터 사용

## 문제 해결

### 인증 오류 (401 Unauthorized)
```
Error: 401 Unauthorized
```

**해결 방법:**
- Client ID와 Secret이 정확한지 확인
- OAuth Client가 활성화되어 있는지 확인
- 계정이 유효한지 확인 (Trial 기간 확인)

### 이미지를 찾을 수 없음
```
Warning: No images found for the given criteria
```

**해결 방법:**
- 시간 범위를 더 넓게 설정 (예: 60일)
- 다른 날짜 시도
- 구름이 적은 날씨 선택
- 좌표가 올바른지 확인

### 할당량 초과
```
Error: Processing units quota exceeded
```

**해결 방법:**
- Dashboard에서 사용량 확인
- 다음 달까지 대기
- 유료 플랜으로 업그레이드 고려

### 느린 다운로드 속도
- 이미지 해상도를 낮춤 (10m → 20m)
- BBox 크기를 작게 설정
- 밴드 수를 줄임 (필요한 것만)

## 추가 리소스

### 공식 문서
- [Sentinel Hub Documentation](https://docs.sentinel-hub.com/)
- [Python Package Docs](https://sentinelhub-py.readthedocs.io/)
- [API Reference](https://docs.sentinel-hub.com/api/latest/)

### 튜토리얼
- [Getting Started](https://docs.sentinel-hub.com/api/latest/user-guides/getting-started/)
- [Evalscript Examples](https://custom-scripts.sentinel-hub.com/)
- [Process API](https://docs.sentinel-hub.com/api/latest/api/process/)

### 커뮤니티
- [Forum](https://forum.sentinel-hub.com/)
- [GitHub Issues](https://github.com/sentinel-hub/sentinelhub-py/issues)

## 다음 단계

설정이 완료되었다면:
1. `example_simple.py`로 첫 이미지 다운로드
2. `example_advanced.py`로 다양한 분석 시도
3. 자신만의 evalscript 작성
4. 프로젝트에 통합

Happy Coding! 🛰️
