# Sentinel-2A Image Downloader

Sentinel Hub API를 사용하여 Sentinel-2A 위성 이미지를 다운로드하는 Python 프로젝트입니다.

## 특징

- ✅ Sentinel Hub API를 통한 고품질 위성 이미지 다운로드
- ✅ True Color RGB 이미지 생성
- ✅ 개별 밴드 다운로드 지원
- ✅ 사용자 정의 evalscript 지원
- ✅ 다양한 출력 형식 (TIFF, PNG 등)
- ✅ 유연한 해상도 및 지역 설정

## 필요 조건

- Python 3.7 이상
- Sentinel Hub 계정 및 API 자격 증명

## 설치 방법

### 1. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. Sentinel Hub 계정 설정

1. [Sentinel Hub](https://apps.sentinel-hub.com/) 에서 무료 계정 생성
2. Dashboard에서 OAuth Client 생성
3. Client ID와 Client Secret 발급

### 3. 설정 파일 생성

```bash
cp config_example.py config.py
```

그리고 `config.py` 파일에 발급받은 자격 증명을 입력합니다.

## 사용 방법

### 기본 사용

```python
from sentinel_downloader import SentinelDownloader
from datetime import datetime, timedelta

# 다운로더 초기화
downloader = SentinelDownloader(
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# 지역 설정 (서울 예제)
bbox_coords = (126.9, 37.4, 127.1, 37.6)  # (min_lon, min_lat, max_lon, max_lat)

# 기간 설정 (최근 30일)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
time_interval = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

# True Color RGB 이미지 다운로드
filepath = downloader.download_image(
    bbox_coords=bbox_coords,
    time_interval=time_interval,
    output_path="images",
    resolution=10
)

print(f"이미지 저장 완료: {filepath}")
```

### 개별 밴드 다운로드

```python
# 특정 밴드만 다운로드
bands = ["B02", "B03", "B04", "B08"]  # Blue, Green, Red, NIR

downloaded_files = downloader.download_multiple_bands(
    bbox_coords=bbox_coords,
    time_interval=time_interval,
    bands=bands,
    output_path="bands",
    resolution=10
)

for band, filepath in downloaded_files.items():
    print(f"{band}: {filepath}")
```

### 커스텀 Evalscript 사용

```python
# NDVI 계산 예제
ndvi_evalscript = """
//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["B04", "B08"],
            units: "DN"
        }],
        output: {
            bands: 1,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(sample) {
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    return [ndvi];
}
"""

filepath = downloader.download_image(
    bbox_coords=bbox_coords,
    time_interval=time_interval,
    evalscript=ndvi_evalscript,
    output_path="ndvi_images"
)
```

## Sentinel-2 밴드 정보

| 밴드 | 설명 | 해상도 | 파장 (nm) |
|------|------|--------|-----------|
| B01 | Coastal aerosol | 60m | 443 |
| B02 | Blue | 10m | 490 |
| B03 | Green | 10m | 560 |
| B04 | Red | 10m | 665 |
| B05 | Vegetation Red Edge | 20m | 705 |
| B06 | Vegetation Red Edge | 20m | 740 |
| B07 | Vegetation Red Edge | 20m | 783 |
| B08 | NIR | 10m | 842 |
| B8A | Narrow NIR | 20m | 865 |
| B09 | Water vapour | 60m | 945 |
| B10 | SWIR - Cirrus | 60m | 1375 |
| B11 | SWIR | 20m | 1610 |
| B12 | SWIR | 20m | 2190 |

## 주요 클래스 및 메서드

### SentinelDownloader

#### `__init__(client_id, client_secret, instance_id=None)`
다운로더 초기화

**매개변수:**
- `client_id`: Sentinel Hub OAuth 클라이언트 ID
- `client_secret`: Sentinel Hub OAuth 클라이언트 시크릿
- `instance_id`: Sentinel Hub 인스턴스 ID (선택사항)

#### `download_image(bbox_coords, time_interval, output_path, resolution, image_format, evalscript)`
단일 이미지 다운로드

**매개변수:**
- `bbox_coords`: 경계 상자 좌표 튜플 (min_lon, min_lat, max_lon, max_lat)
- `time_interval`: 시간 범위 튜플 (start_date, end_date)
- `output_path`: 출력 디렉토리 경로
- `resolution`: 이미지 해상도 (미터 단위)
- `image_format`: 출력 형식 (MimeType.TIFF, MimeType.PNG 등)
- `evalscript`: 커스텀 evalscript (선택사항)

**반환값:** 저장된 파일 경로

#### `download_multiple_bands(bbox_coords, time_interval, bands, output_path, resolution)`
여러 밴드를 개별 파일로 다운로드

**매개변수:**
- `bbox_coords`: 경계 상자 좌표
- `time_interval`: 시간 범위
- `bands`: 밴드 리스트 (예: ['B02', 'B03', 'B04'])
- `output_path`: 출력 디렉토리 경로
- `resolution`: 이미지 해상도

**반환값:** {밴드명: 파일경로} 딕셔너리

## 예제 실행

```bash
# 기본 예제 실행 (설정 파일 필요)
python sentinel_downloader.py
```

## 문제 해결

### API 자격 증명 오류
- Sentinel Hub Dashboard에서 OAuth Client 정보 확인
- Client ID와 Client Secret이 올바른지 확인

### 이미지를 찾을 수 없음
- 시간 범위를 더 넓게 설정 (예: 60일)
- 구름 커버가 낮은 날짜 선택
- 지역 좌표가 올바른지 확인

### 메모리 부족
- 이미지 해상도를 낮춤 (예: 10m → 20m)
- 다운로드 지역을 작게 설정

## 참고 자료

- [Sentinel Hub Documentation](https://docs.sentinel-hub.com/)
- [Sentinel Hub Python Package](https://sentinelhub-py.readthedocs.io/)
- [Sentinel-2 User Handbook](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi)
- [Evalscript V3 Documentation](https://docs.sentinel-hub.com/api/latest/evalscript/v3/)

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트 환영합니다!
