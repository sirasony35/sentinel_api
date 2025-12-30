import os
import traceback  # 상세 에러 확인용
import numpy as np
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    SentinelHubCatalog,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    bbox_to_dimensions,
)

# ---------------------------------------------------------
# 1. 설정
# ---------------------------------------------------------
CLIENT_ID = '2602a8dc-bdc6-4dca-a1eb-9a8a0c9f6b30'
CLIENT_SECRET = 'oofByVn5fbUMrkJLWRlZOv29T4EMdHdc'

FARM_ID = "Verification_Test"
TARGET_DATE = "2025-08-23"
raw_bbox = [127.492432, 36.869177, 127.481609, 36.879132]

# ---------------------------------------------------------
# 2. 초기화
# ---------------------------------------------------------
config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET

min_lon, max_lon = min(raw_bbox[0], raw_bbox[2]), max(raw_bbox[0], raw_bbox[2])
min_lat, max_lat = min(raw_bbox[1], raw_bbox[3]), max(raw_bbox[1], raw_bbox[3])
farm_bbox = BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)
farm_size = bbox_to_dimensions(farm_bbox, resolution=10)

print(f"🕵️ '{TARGET_DATE}' 데이터 정밀 진단 시작...\n")

# ---------------------------------------------------------
# 3. 이미지 다운로드 (가장 단순한 형태)
# ---------------------------------------------------------
print("📸 이미지 데이터 요청 중...")

# 오류 원인을 줄이기 위해 딱 1개(RGB)만 요청합니다.
evalscript_debug = """
function setup() {
  return {
    input: ["B04", "B03", "B02", "dataMask"],
    output: { id: "RGB", bands: 3, sampleType: "UINT8" }, // List([])가 아닌 객체({})로 단순화
    mosaicking: "ORBIT"
  };
}

function evaluatePixel(samples) {
  // 데이터 없음 방어 로직
  if (samples.length === 0) return [0, 0, 0];

  var sample = samples[0];
  if (!sample.dataMask || sample.dataMask === 0) return [0, 0, 0];

  // 값 추출
  var r = Math.round(sample.B04 * 2.5 * 255);
  var g = Math.round(sample.B03 * 2.5 * 255);
  var b = Math.round(sample.B02 * 2.5 * 255);

  // 255 초과 방지
  return [Math.min(r, 255), Math.min(g, 255), Math.min(b, 255)];
}
"""

request = SentinelHubRequest(
    evalscript=evalscript_debug,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=(TARGET_DATE, TARGET_DATE),
            mosaicking_order='leastCC'
        )
    ],
    responses=[
        SentinelHubRequest.output_response('RGB', MimeType.PNG)
    ],
    bbox=farm_bbox,
    size=farm_size,
    config=config
)

try:
    # 1. 데이터 받아오기
    data = request.get_data()

    # 2. 데이터 구조 확인 (디버깅의 핵심)
    print("\n" + "=" * 40)
    print(f"🧐 데이터 수신 상태 확인")
    print("=" * 40)
    print(f" - 데이터 타입: {type(data)}")
    print(f" - 데이터 길이(Len): {len(data) if isinstance(data, list) else 'Not a list'}")

    if isinstance(data, list) and len(data) > 0:
        print(f" - 첫 번째 데이터 크기: {data[0].shape if hasattr(data[0], 'shape') else 'Unknown'}")

        # 0값(검은색) 비율 확인
        img = data[0]
        zero_pixels = np.count_nonzero(img == 0)
        total_pixels = img.size
        print(f" - 검은색(0) 픽셀 비율: {zero_pixels / total_pixels * 100:.2f}%")

        if zero_pixels == total_pixels:
            print("\n🚨 [진단 결과] 완전한 검은색 이미지입니다.")
            print("   -> 위성 사진이 이 지역을 커버하지 못했습니다. (데이터 없음)")
        else:
            print("\n✅ [진단 결과] 유효한 이미지가 생성되었습니다.")

    else:
        print("\n🚨 [진단 결과] 빈 리스트([])가 반환되었습니다.")
        print("   -> Sentinel Hub 서버가 이 좌표에 줄 수 있는 데이터가 없다고 판단했습니다.")
        print("   -> 원인: 농장이 위성 촬영 경로(Swath)의 바깥쪽 여백에 위치함.")

except Exception:
    print("\n❌ [시스템 에러 발생]")
    # 에러의 정확한 위치를 추적하여 출력
    traceback.print_exc()