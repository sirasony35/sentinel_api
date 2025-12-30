import os
import tarfile
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    bbox_to_dimensions,
)

# ---------------------------------------------------------
# 1. 설정 및 입력 변수
# ---------------------------------------------------------
# [보안] 재발급 받은 키를 입력하세요
CLIENT_ID = '2602a8dc-bdc6-4dca-a1eb-9a8a0c9f6b30'
CLIENT_SECRET = 'oofByVn5fbUMrkJLWRlZOv29T4EMdHdc'

FARM_ID = "Farm_Final_Run"
OUTPUT_FOLDER = 'farm_data_complete'  # 저장될 메인 폴더

# 입력하신 좌표
raw_bbox = [127.492432, 36.869177, 127.481609, 36.879132]

# BBox 좌표 정렬
min_lon = min(raw_bbox[0], raw_bbox[2])
max_lon = max(raw_bbox[0], raw_bbox[2])
min_lat = min(raw_bbox[1], raw_bbox[3])
max_lat = max(raw_bbox[1], raw_bbox[3])
FARM_BBOX = [min_lon, min_lat, max_lon, max_lat]

# ---------------------------------------------------------
# 2. 초기화
# ---------------------------------------------------------
config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

farm_bbox_obj = BBox(bbox=FARM_BBOX, crs=CRS.WGS84)
farm_size = bbox_to_dimensions(farm_bbox_obj, resolution=10)

# ---------------------------------------------------------
# 3. Evalscript (ORBIT 방식)
# ---------------------------------------------------------
evalscript_indices = """
function setup() {
  return {
    input: ["B02", "B03", "B04", "B05", "B08", "B11", "dataMask"],
    output: [
      { id: "RGB",   bands: 3, sampleType: "FLOAT32" },
      { id: "NDVI",  bands: 1, sampleType: "FLOAT32" },
      { id: "NDMI",  bands: 1, sampleType: "FLOAT32" },
      { id: "GNDVI", bands: 1, sampleType: "FLOAT32" },
      { id: "OSAVI", bands: 1, sampleType: "FLOAT32" },
      { id: "NDRE",  bands: 1, sampleType: "FLOAT32" },
      { id: "LCI",   bands: 1, sampleType: "FLOAT32" }
    ],
    mosaicking: "ORBIT"
  };
}

function evaluatePixel(samples) {
  if (samples.length === 0) {
    return { RGB: [0,0,0], NDVI: [0], NDMI: [0], GNDVI: [0], OSAVI: [0], NDRE: [0], LCI: [0] };
  }
  var sample = samples[0];
  if (!sample.dataMask || sample.dataMask === 0) {
    return { RGB: [0,0,0], NDVI: [0], NDMI: [0], GNDVI: [0], OSAVI: [0], NDRE: [0], LCI: [0] };
  }

  var b02 = sample.B02 || 0;
  var b03 = sample.B03 || 0;
  var b04 = sample.B04 || 0;
  var b05 = sample.B05 || 0;
  var b08 = sample.B08 || 0;
  var b11 = sample.B11 || 0;

  var val_ndvi = (b08 + b04 === 0) ? 0 : (b08 - b04) / (b08 + b04);
  var val_ndmi = (b08 + b11 === 0) ? 0 : (b08 - b11) / (b08 + b11);
  var val_gndvi = (b08 + b03 === 0) ? 0 : (b08 - b03) / (b08 + b03);
  var osavi_denom = b08 + b04 + 0.16;
  var val_osavi = (osavi_denom === 0) ? 0 : (1.16 * (b08 - b04)) / osavi_denom;
  var val_ndre = (b08 + b05 === 0) ? 0 : (b08 - b05) / (b08 + b05);
  var val_lci = (b08 + b04 === 0) ? 0 : (b08 - b05) / (b08 + b04);
  var val_rgb = [b04 * 2.5, b03 * 2.5, b02 * 2.5];

  return {
    RGB: val_rgb, NDVI: [val_ndvi], NDMI: [val_ndmi],
    GNDVI: [val_gndvi], OSAVI: [val_osavi], NDRE: [val_ndre], LCI: [val_lci]
  };
}
"""

# ---------------------------------------------------------
# 4. 데이터 요청 객체 생성
# ---------------------------------------------------------
my_identifiers = ["RGB", "NDVI", "NDMI", "GNDVI", "OSAVI", "NDRE", "LCI"]

request = SentinelHubRequest(
    evalscript=evalscript_indices,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=('2024-06-01', '2024-07-15'),
            mosaicking_order='leastCC'
        )
    ],
    responses=[
        SentinelHubRequest.output_response(name, MimeType.TIFF) for name in my_identifiers
    ],
    bbox=farm_bbox_obj,
    size=farm_size,
    config=config,
    data_folder=OUTPUT_FOLDER
)

print(f"📡 '{FARM_ID}'의 데이터 다운로드를 시작합니다...")

# ---------------------------------------------------------
# 5. 다운로드 및 [경로 보정] 및 압축 해제 (경고 수정됨)
# ---------------------------------------------------------
try:
    # 1. 다운로드 실행
    data = request.get_data(save_data=True)
    saved_paths = request.get_filename_list()

    # 경로 보정 로직
    relative_tar_path = saved_paths[0]

    if os.path.exists(relative_tar_path):
        tar_path = relative_tar_path
    else:
        tar_path = os.path.join(OUTPUT_FOLDER, relative_tar_path)

    print(f"🔎 파일 위치 확인: {os.path.abspath(tar_path)}")

    # 2. 압축 해제
    if tar_path.endswith('.tar') and os.path.exists(tar_path):
        folder_path = os.path.dirname(tar_path)

        print(f"\n📦 압축 파일 감지: {os.path.basename(tar_path)}")
        print("📂 압축을 해제하고 있습니다...")

        with tarfile.open(tar_path) as tar:
            # [수정됨] filter='data' 추가하여 DeprecationWarning 해결
            # Python 3.12 이상에서 권장되는 보안 옵션입니다.
            tar.extractall(path=folder_path, filter='data')

        print("✅ 압축 해제 완료!")

        # 3. 파일 이름 변경
        print("\n🔄 파일 이름 정리 중...")
        for identifier in my_identifiers:
            old_name = f"{identifier}.tif"
            old_file_path = os.path.join(folder_path, old_name)

            new_name = f"20240601_{FARM_ID}_{identifier}.tif"
            new_file_path = os.path.join(folder_path, new_name)

            if os.path.exists(old_file_path):
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                os.rename(old_file_path, new_file_path)
                print(f"✅ 생성 완료: {new_name}")
            else:
                print(f"⚠️ {old_name} 파일을 찾을 수 없습니다. (폴더: {folder_path})")

    else:
        print(f"\n❌ 오류: 파일을 찾을 수 없습니다.\n경로: {tar_path}")

    print(f"\n🎉 모든 처리가 완료되었습니다. '{OUTPUT_FOLDER}' 폴더를 확인하세요.")

except Exception as e:
    print(f"\n❌ 시스템 오류 발생: {e}")