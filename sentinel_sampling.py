import os
import tarfile
import datetime
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

# =============================================================================
# [1] 사용자 설정 (USER CONFIGURATION)
# =============================================================================
# ★ 보안: 실제 운영 시에는 환경 변수나 별도 config 파일에서 불러오는 것을 권장합니다.
CLIENT_ID = '2602a8dc-bdc6-4dca-a1eb-9a8a0c9f6b30'
CLIENT_SECRET = 'oofByVn5fbUMrkJLWRlZOv29T4EMdHdc'

# 대상 농장 ID
FARM_ID = "GJ_Rice_Field_01"

# 데이터 저장 경로
OUTPUT_FOLDER = 'sentinel_timeseries_data'

# 분석 기간 설정 (시계열)
START_DATE = "2025-06-01"
END_DATE = "2025-10-10"

# 농경지 좌표 (김제시 예시)
RAW_BBOX = [127.492432, 36.869177, 127.481609, 36.879132]

# [중요] 구름 허용 한계치 (0.0 ~ 100.0)
# 촬영된 이미지 중 구름이 이 값(%)보다 많은 날은 다운로드하지 않고 건너뜁니다.
MAX_CC_PERCENT = 30.0

# 추출할 지수 목록
TARGET_INDICES = ["RGB", "NDVI", "NDMI", "GNDVI", "OSAVI", "NDRE", "LCI"]

# =============================================================================
# [2] 초기화 및 유틸리티 설정
# =============================================================================
config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# BBox 정렬 (좌,하,우,상)
min_lon, max_lon = min(RAW_BBOX[0], RAW_BBOX[2]), max(RAW_BBOX[0], RAW_BBOX[2])
min_lat, max_lat = min(RAW_BBOX[1], RAW_BBOX[3]), max(RAW_BBOX[1], RAW_BBOX[3])
farm_bbox = BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)
farm_size = bbox_to_dimensions(farm_bbox, resolution=10)

# =============================================================================
# [3] Evalscript (Production용: 안전 모드)
# =============================================================================
EVALSCRIPT = """
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
  if (samples.length === 0) return createZero();

  var sample = samples[0];
  if (!sample.dataMask || sample.dataMask === 0) return createZero();

  var b02 = sample.B02 || 0;
  var b03 = sample.B03 || 0;
  var b04 = sample.B04 || 0;
  var b05 = sample.B05 || 0;
  var b08 = sample.B08 || 0;
  var b11 = sample.B11 || 0;

  var val_ndvi = calcIndex(b08, b04);
  var val_ndmi = calcIndex(b08, b11);
  var val_gndvi = calcIndex(b08, b03);
  var val_ndre = calcIndex(b08, b05);
  var val_lci = calcIndex(b08, b04, b05); // LCI special

  // OSAVI
  var osavi_denom = b08 + b04 + 0.16;
  var val_osavi = (osavi_denom === 0) ? 0 : (1.16 * (b08 - b04)) / osavi_denom;

  var val_rgb = [b04 * 2.5, b03 * 2.5, b02 * 2.5];

  return {
    RGB: val_rgb, NDVI: [val_ndvi], NDMI: [val_ndmi],
    GNDVI: [val_gndvi], OSAVI: [val_osavi], NDRE: [val_ndre], LCI: [val_lci]
  };
}

// 헬퍼 함수
function calcIndex(nir, other, other2) {
    if (other2 !== undefined) { // For LCI
        return (nir + other === 0) ? 0 : (nir - other2) / (nir + other);
    }
    return (nir + other === 0) ? 0 : (nir - other) / (nir + other);
}

function createZero() {
    return { RGB: [0,0,0], NDVI: [0], NDMI: [0], GNDVI: [0], OSAVI: [0], NDRE: [0], LCI: [0] };
}
"""

# =============================================================================
# [4] Catalog API를 통한 촬영 날짜 검색 및 필터링
# =============================================================================
print(f"🔍 Sentinel-2 촬영 목록 조회 중... ({START_DATE} ~ {END_DATE})")

catalog = SentinelHubCatalog(config=config)
search_iterator = catalog.search(
    collection=DataCollection.SENTINEL2_L2A,
    time=(START_DATE, END_DATE),
    bbox=farm_bbox,
    fields={"include": ["id", "properties.datetime", "properties.eo:cloud_cover"], "exclude": []}
)

# 유효한 날짜 목록 추출
valid_dates = []
for feature in search_iterator:
    obs_date_str = feature["properties"]["datetime"]
    cloud_cover = feature["properties"]["eo:cloud_cover"]

    # 구름 필터링
    if cloud_cover <= MAX_CC_PERCENT:
        # ISO 포맷 날짜에서 YYYY-MM-DD 추출
        dt_obj = datetime.datetime.fromisoformat(obs_date_str.replace('Z', '+00:00'))
        date_str = dt_obj.strftime("%Y-%m-%d")  # 날짜 (YYYY-MM-DD)
        time_str = dt_obj.strftime("%H:%M:%S")  # 시간 (HH:MM:SS)

        # 같은 날짜 중복 제거 (타일이 여러 개일 경우 대비)
        if date_str not in [d['date'] for d in valid_dates]:
            valid_dates.append({
                'date': date_str,
                'time': time_str,
                'cloud': cloud_cover
            })

# 날짜순 정렬 (과거 -> 현재)
valid_dates.sort(key=lambda x: x['date'])

print(f"✅ 총 {len(valid_dates)}개의 유효한 촬영 날짜를 찾았습니다. (구름 {MAX_CC_PERCENT}% 이하)")
for item in valid_dates:
    print(f"   - {item['date']} {item['time']} UTC (구름: {item['cloud']:.2f}%)")

# =============================================================================
# [5] 날짜별 순차 다운로드 (Loop)
# =============================================================================
for idx, item in enumerate(valid_dates):
    target_date = item['date']
    print(f"\n🚀 [{idx + 1}/{len(valid_dates)}] 다운로드 시작: {target_date} ...")

    # 해당 날짜의 00:00 ~ 23:59 설정
    # time_interval을 하루 단위로 지정하면 해당 일자의 이미지를 가져옵니다.
    request_interval = (target_date, target_date)

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=request_interval,
                mosaicking_order='leastCC'
            )
        ],
        responses=[
            SentinelHubRequest.output_response(name, MimeType.TIFF) for name in TARGET_INDICES
        ],
        bbox=farm_bbox,
        size=farm_size,
        config=config,
        data_folder=OUTPUT_FOLDER
    )

    try:
        # 1. 데이터 다운로드
        data = request.get_data(save_data=True)
        saved_paths = request.get_filename_list()

        # 2. 파일 처리 (압축 해제 및 리네이밍)
        relative_tar_path = saved_paths[0]
        if os.path.exists(relative_tar_path):
            tar_path = relative_tar_path
        else:
            tar_path = os.path.join(OUTPUT_FOLDER, relative_tar_path)

        if tar_path.endswith('.tar') and os.path.exists(tar_path):
            folder_path = os.path.dirname(tar_path)

            # 압축 해제
            with tarfile.open(tar_path) as tar:
                tar.extractall(path=folder_path, filter='data')

            # 파일 리네이밍: YYYYMMDD_FarmID_Index.tif
            date_clean = target_date.replace("-", "")  # 20240601

            for identifier in TARGET_INDICES:
                old_name = f"{identifier}.tif"
                old_file_path = os.path.join(folder_path, old_name)

                new_name = f"{date_clean}_{FARM_ID}_{identifier}.tif"
                new_file_path = os.path.join(folder_path, new_name)

                if os.path.exists(old_file_path):
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                    os.rename(old_file_path, new_file_path)

            # 원본 tar 파일 삭제 (선택 사항 - 공간 절약을 위해 주석 해제 권장)
            os.remove(tar_path)
            print(f"   ✅ 처리 완료: {date_clean} 데이터 저장됨.")

        else:
            print(f"   ⚠️ 경고: 압축 파일이 발견되지 않았습니다.")

    except Exception as e:
        print(f"   ❌ {target_date} 다운로드 실패: {e}")

print(f"\n🎉 모든 시계열 데이터 수집이 완료되었습니다! ('{OUTPUT_FOLDER}')")