#!/usr/bin/env python3
"""
고급 Sentinel-2A 이미지 다운로드 예제
- 여러 밴드 다운로드
- NDVI 계산
- 커스텀 evalscript 사용
"""

from sentinel_downloader import SentinelDownloader
from datetime import datetime, timedelta
from sentinelhub import MimeType

# 자격 증명 (config.py가 있다면 그것을 import 할 수도 있습니다)
try:
    from config import SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET
    CLIENT_ID = SENTINEL_HUB_CLIENT_ID
    CLIENT_SECRET = SENTINEL_HUB_CLIENT_SECRET
except ImportError:
    CLIENT_ID = "your_client_id_here"
    CLIENT_SECRET = "your_client_secret_here"


def download_rgb_image(downloader, bbox, time_interval):
    """True Color RGB 이미지 다운로드"""
    print("\n" + "="*60)
    print("1. True Color RGB 이미지 다운로드")
    print("="*60)
    
    filepath = downloader.download_image(
        bbox_coords=bbox,
        time_interval=time_interval,
        output_path="images/rgb",
        resolution=10,
        image_format=MimeType.PNG
    )
    
    return filepath


def download_individual_bands(downloader, bbox, time_interval):
    """개별 밴드 다운로드"""
    print("\n" + "="*60)
    print("2. 개별 밴드 다운로드")
    print("="*60)
    
    bands = ["B02", "B03", "B04", "B08"]  # Blue, Green, Red, NIR
    
    downloaded_files = downloader.download_multiple_bands(
        bbox_coords=bbox,
        time_interval=time_interval,
        bands=bands,
        output_path="images/bands",
        resolution=10
    )
    
    return downloaded_files


def download_ndvi_image(downloader, bbox, time_interval):
    """NDVI (Normalized Difference Vegetation Index) 이미지 다운로드"""
    print("\n" + "="*60)
    print("3. NDVI 이미지 다운로드")
    print("="*60)
    
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
        bbox_coords=bbox,
        time_interval=time_interval,
        output_path="images/ndvi",
        resolution=10,
        image_format=MimeType.TIFF,
        evalscript=ndvi_evalscript
    )
    
    return filepath


def download_false_color_image(downloader, bbox, time_interval):
    """False Color 이미지 다운로드 (식생 강조)"""
    print("\n" + "="*60)
    print("4. False Color 이미지 다운로드 (식생 강조)")
    print("="*60)
    
    false_color_evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B03", "B04", "B08"],
                    units: "DN"
                }],
                output: {
                    bands: 3,
                    sampleType: "AUTO"
                }
            };
        }
        
        function evaluatePixel(sample) {
            // NIR, Red, Green 조합 (식생이 빨간색으로 표시됨)
            return [sample.B08 * 2.5, sample.B04 * 2.5, sample.B03 * 2.5];
        }
    """
    
    filepath = downloader.download_image(
        bbox_coords=bbox,
        time_interval=time_interval,
        output_path="images/false_color",
        resolution=10,
        image_format=MimeType.PNG,
        evalscript=false_color_evalscript
    )
    
    return filepath


def download_moisture_index(downloader, bbox, time_interval):
    """수분 지수 (Moisture Index) 이미지 다운로드"""
    print("\n" + "="*60)
    print("5. 수분 지수 (Moisture Index) 이미지 다운로드")
    print("="*60)
    
    moisture_evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: [{
                    bands: ["B8A", "B11"],
                    units: "DN"
                }],
                output: {
                    bands: 1,
                    sampleType: "FLOAT32"
                }
            };
        }
        
        function evaluatePixel(sample) {
            // NDMI = (NIR - SWIR) / (NIR + SWIR)
            let ndmi = (sample.B8A - sample.B11) / (sample.B8A + sample.B11);
            return [ndmi];
        }
    """
    
    filepath = downloader.download_image(
        bbox_coords=bbox,
        time_interval=time_interval,
        output_path="images/moisture",
        resolution=20,  # B8A와 B11은 20m 해상도
        image_format=MimeType.TIFF,
        evalscript=moisture_evalscript
    )
    
    return filepath


def main():
    """메인 함수"""
    
    # 다운로드할 지역 설정
    # 예제 1: 서울
    seoul_bbox = (126.9, 37.4, 127.1, 37.6)
    
    # 예제 2: 제주도
    # jeju_bbox = (126.3, 33.3, 126.7, 33.6)
    
    # 사용할 지역 선택
    bbox = seoul_bbox
    
    # 기간 설정 (최근 30일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    time_interval = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    
    print("="*60)
    print("Sentinel-2A 고급 이미지 다운로드 예제")
    print("="*60)
    print(f"지역: {bbox}")
    print(f"기간: {time_interval[0]} ~ {time_interval[1]}")
    
    try:
        # 다운로더 초기화
        downloader = SentinelDownloader(CLIENT_ID, CLIENT_SECRET)
        
        # 1. True Color RGB 이미지
        rgb_file = download_rgb_image(downloader, bbox, time_interval)
        
        # 2. 개별 밴드
        band_files = download_individual_bands(downloader, bbox, time_interval)
        
        # 3. NDVI
        ndvi_file = download_ndvi_image(downloader, bbox, time_interval)
        
        # 4. False Color
        false_color_file = download_false_color_image(downloader, bbox, time_interval)
        
        # 5. Moisture Index
        moisture_file = download_moisture_index(downloader, bbox, time_interval)
        
        # 결과 요약
        print("\n" + "="*60)
        print("다운로드 완료!")
        print("="*60)
        
        print(f"\n✓ RGB 이미지: {rgb_file}")
        print(f"✓ NDVI 이미지: {ndvi_file}")
        print(f"✓ False Color 이미지: {false_color_file}")
        print(f"✓ Moisture Index 이미지: {moisture_file}")
        
        print("\n✓ 개별 밴드:")
        for band, filepath in band_files.items():
            print(f"  - {band}: {filepath}")
            
    except ValueError as e:
        print(f"\n설정 오류: {str(e)}")
        print("\n사용 방법:")
        print("1. https://apps.sentinel-hub.com/ 에서 계정 생성")
        print("2. OAuth Client 자격 증명 발급")
        print("3. config.py 파일을 생성하거나 이 파일의 CLIENT_ID와 CLIENT_SECRET 업데이트")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
