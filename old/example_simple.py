#!/usr/bin/env python3
"""
간단한 Sentinel-2A 이미지 다운로드 예제
"""

from sentinel_downloader import SentinelDownloader
from datetime import datetime, timedelta
from sentinelhub import MimeType

# ===== 여기에 당신의 자격 증명을 입력하세요 =====
CLIENT_ID = "your_client_id_here"
CLIENT_SECRET = "your_client_secret_here"

# ===== 다운로드 설정 =====
# 서울 지역 좌표 (경도, 위도)
bbox_coords = (126.9, 37.4, 127.1, 37.6)

# 최근 30일 기간 설정
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
time_interval = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

# ===== 이미지 다운로드 =====
if __name__ == "__main__":
    try:
        print("Sentinel-2A 이미지 다운로드 시작...\n")
        
        # 다운로더 생성
        downloader = SentinelDownloader(CLIENT_ID, CLIENT_SECRET)
        
        # True Color 이미지 다운로드
        print("True Color RGB 이미지 다운로드 중...")
        filepath = downloader.download_image(
            bbox_coords=bbox_coords,
            time_interval=time_interval,
            output_path="images",
            resolution=10,
            image_format=MimeType.PNG
        )
        
        if filepath:
            print(f"\n✓ 다운로드 성공!")
            print(f"저장 위치: {filepath}")
        else:
            print("\n해당 조건에 맞는 이미지를 찾을 수 없습니다.")
            print("기간을 더 넓게 설정하거나 다른 지역을 시도해보세요.")
            
    except ValueError as e:
        print(f"\n설정 오류: {str(e)}")
        print("\n사용 방법:")
        print("1. https://apps.sentinel-hub.com/ 에서 계정 생성")
        print("2. OAuth Client 자격 증명 발급")
        print("3. 이 파일의 CLIENT_ID와 CLIENT_SECRET 값 업데이트")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
