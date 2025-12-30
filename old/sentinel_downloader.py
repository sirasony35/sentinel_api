#!/usr/bin/env python3
"""
Sentinel-2A Image Downloader using Sentinel Hub API
This script downloads Sentinel-2A satellite imagery for a specified area and time period.
"""

import os
from datetime import datetime, timedelta
from sentinelhub import (
    SHConfig,
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)


class SentinelDownloader:
    """Sentinel-2A 이미지 다운로더 클래스"""
    
    def __init__(self, client_id, client_secret, instance_id=None):
        """
        초기화
        
        Args:
            client_id (str): Sentinel Hub OAuth 클라이언트 ID
            client_secret (str): Sentinel Hub OAuth 클라이언트 시크릿
            instance_id (str, optional): Sentinel Hub 인스턴스 ID
        """
        self.config = SHConfig()
        self.config.sh_client_id = client_id
        self.config.sh_client_secret = client_secret
        if instance_id:
            self.config.instance_id = instance_id
        
        # 설정 확인
        if not self.config.sh_client_id or not self.config.sh_client_secret:
            raise ValueError("Sentinel Hub credentials are required!")
    
    def download_image(
        self,
        bbox_coords,
        time_interval,
        output_path="sentinel_images",
        resolution=10,
        image_format=MimeType.TIFF,
        evalscript=None
    ):
        """
        Sentinel-2A 이미지 다운로드
        
        Args:
            bbox_coords (tuple): 경계 상자 좌표 (min_lon, min_lat, max_lon, max_lat)
            time_interval (tuple): 시간 범위 (start_date, end_date) - 'YYYY-MM-DD' 형식
            output_path (str): 출력 디렉토리 경로
            resolution (int): 이미지 해상도 (미터 단위)
            image_format (MimeType): 출력 이미지 형식
            evalscript (str, optional): 커스텀 evalscript
        
        Returns:
            str: 저장된 이미지 파일 경로
        """
        # 출력 디렉토리 생성
        os.makedirs(output_path, exist_ok=True)
        
        # 경계 상자 설정 (WGS84 좌표계)
        bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
        
        # 이미지 크기 계산
        size = bbox_to_dimensions(bbox, resolution=resolution)
        print(f"이미지 크기: {size}")
        
        # 기본 evalscript (True Color RGB)
        if evalscript is None:
            evalscript = """
                //VERSION=3
                function setup() {
                    return {
                        input: [{
                            bands: ["B02", "B03", "B04", "B08"],
                            units: "DN"
                        }],
                        output: {
                            bands: 4,
                            sampleType: "AUTO"
                        }
                    };
                }
                
                function evaluatePixel(sample) {
                    return [sample.B04, sample.B03, sample.B02, sample.B08];
                }
            """
        
        # SentinelHub 요청 생성
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=time_interval,
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", image_format)
            ],
            bbox=bbox,
            size=size,
            config=self.config,
        )
        
        # 이미지 다운로드
        print(f"이미지 다운로드 중...")
        print(f"지역: {bbox_coords}")
        print(f"기간: {time_interval}")
        
        try:
            image_data = request.get_data()
            
            if not image_data or len(image_data) == 0:
                print("경고: 해당 조건에 맞는 이미지를 찾을 수 없습니다.")
                return None
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "tif" if image_format == MimeType.TIFF else "png"
            filename = f"sentinel2a_{timestamp}.{extension}"
            filepath = os.path.join(output_path, filename)
            
            # 이미지 저장
            with open(filepath, "wb") as f:
                if image_format == MimeType.TIFF:
                    f.write(image_data[0])
                else:
                    f.write(image_data[0])
            
            print(f"✓ 이미지 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            raise
    
    def download_multiple_bands(
        self,
        bbox_coords,
        time_interval,
        bands,
        output_path="sentinel_images",
        resolution=10
    ):
        """
        여러 밴드를 개별적으로 다운로드
        
        Args:
            bbox_coords (tuple): 경계 상자 좌표
            time_interval (tuple): 시간 범위
            bands (list): 다운로드할 밴드 리스트 (예: ['B02', 'B03', 'B04'])
            output_path (str): 출력 디렉토리 경로
            resolution (int): 이미지 해상도
        
        Returns:
            dict: {밴드명: 파일경로} 딕셔너리
        """
        downloaded_files = {}
        
        for band in bands:
            evalscript = f"""
                //VERSION=3
                function setup() {{
                    return {{
                        input: [{{
                            bands: ["{band}"],
                            units: "DN"
                        }}],
                        output: {{
                            bands: 1,
                            sampleType: "AUTO"
                        }}
                    }};
                }}
                
                function evaluatePixel(sample) {{
                    return [sample.{band}];
                }}
            """
            
            print(f"\n밴드 {band} 다운로드 중...")
            
            bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
            size = bbox_to_dimensions(bbox, resolution=resolution)
            
            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=time_interval,
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response("default", MimeType.TIFF)
                ],
                bbox=bbox,
                size=size,
                config=self.config,
            )
            
            try:
                image_data = request.get_data()
                
                if image_data and len(image_data) > 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"sentinel2a_{band}_{timestamp}.tif"
                    filepath = os.path.join(output_path, filename)
                    
                    os.makedirs(output_path, exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(image_data[0])
                    
                    downloaded_files[band] = filepath
                    print(f"✓ 밴드 {band} 저장 완료: {filepath}")
                else:
                    print(f"경고: 밴드 {band}에 대한 이미지를 찾을 수 없습니다.")
                    
            except Exception as e:
                print(f"밴드 {band} 다운로드 중 오류: {str(e)}")
        
        return downloaded_files


def main():
    """메인 함수 - 사용 예제"""
    
    # ===== 설정 =====
    # Sentinel Hub 자격 증명 (https://apps.sentinel-hub.com/dashboard/ 에서 발급)
    CLIENT_ID = "your_client_id_here"
    CLIENT_SECRET = "your_client_secret_here"
    
    # 다운로드할 지역 (서울 지역 예제)
    # 형식: (최소경도, 최소위도, 최대경도, 최대위도)
    BBOX_COORDS = (126.9, 37.4, 127.1, 37.6)
    
    # 다운로드할 기간
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    TIME_INTERVAL = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    
    # 출력 디렉토리
    OUTPUT_PATH = "downloaded_images"
    
    # ===== 실행 =====
    try:
        print("=" * 60)
        print("Sentinel-2A Image Downloader")
        print("=" * 60)
        
        # 다운로더 초기화
        downloader = SentinelDownloader(CLIENT_ID, CLIENT_SECRET)
        
        # 예제 1: True Color RGB 이미지 다운로드
        print("\n[예제 1] True Color RGB 이미지 다운로드")
        filepath = downloader.download_image(
            bbox_coords=BBOX_COORDS,
            time_interval=TIME_INTERVAL,
            output_path=OUTPUT_PATH,
            resolution=10,
            image_format=MimeType.PNG
        )
        
        # 예제 2: 특정 밴드들만 다운로드
        print("\n[예제 2] 개별 밴드 다운로드")
        bands = ["B02", "B03", "B04", "B08"]  # Blue, Green, Red, NIR
        downloaded_files = downloader.download_multiple_bands(
            bbox_coords=BBOX_COORDS,
            time_interval=TIME_INTERVAL,
            bands=bands,
            output_path=OUTPUT_PATH,
            resolution=10
        )
        
        print("\n" + "=" * 60)
        print("다운로드 완료!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n설정 오류: {str(e)}")
        print("\n사용 방법:")
        print("1. https://apps.sentinel-hub.com/ 에서 계정 생성")
        print("2. OAuth Client 자격 증명 발급")
        print("3. 코드의 CLIENT_ID와 CLIENT_SECRET 값 업데이트")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")


if __name__ == "__main__":
    main()
