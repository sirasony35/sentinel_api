"""
Sentinel Hub API 설정 예제
이 파일을 config.py로 복사하고 실제 값으로 수정하세요.
"""

# Sentinel Hub OAuth 자격 증명
# https://apps.sentinel-hub.com/dashboard/ 에서 발급받을 수 있습니다.
SENTINEL_HUB_CLIENT_ID = "your_client_id_here"
SENTINEL_HUB_CLIENT_SECRET = "your_client_secret_here"
SENTINEL_HUB_INSTANCE_ID = "your_instance_id_here"  # Optional

# 다운로드 설정
DEFAULT_RESOLUTION = 10  # 미터 단위 (Sentinel-2: 10m, 20m, 60m 가능)
DEFAULT_OUTPUT_PATH = "downloaded_images"

# 관심 지역 예제 (BBox 좌표: min_lon, min_lat, max_lon, max_lat)
SEOUL_BBOX = (126.9, 37.4, 127.1, 37.6)
BUSAN_BBOX = (129.0, 35.0, 129.2, 35.2)
JEJU_BBOX = (126.3, 33.3, 126.7, 33.6)
