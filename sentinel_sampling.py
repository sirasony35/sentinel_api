import os
import glob
import tarfile
import datetime
import urllib3
import requests
import geopandas as gpd
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

# =======================================================================
# [보안 우회 설정] 사내 보안 프로그램으로 인한 SSL 인증 에러 강제 무시
# =======================================================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
old_request = requests.Session.request


def new_request(self, method, url, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, **kwargs)


requests.Session.request = new_request
# =======================================================================

# =============================================================================
# [1] 사용자 설정 (USER CONFIGURATION)
# =============================================================================
# 새로 발급받은 Client ID 적용 완료
CLIENT_ID = '6ca4716a-2747-4773-88fe-6f92aa0cc38c'
CLIENT_SECRET = 'tI5weoZEdReDwFLdoYBSntphmadjJbNc'  # ★ 반드시 수정하세요!

# 데이터 저장 경로
OUTPUT_FOLDER = 'sentinel_timeseries_data'

# POI(관심 지역) 파일들이 들어있는 폴더 경로 (.zip, .shp, .geojson)
AOI_FOLDER_PATH = 'aoi'

# 분석 기간 설정 (시계열)
START_DATE = "2026-01-01"
END_DATE = "2026-03-31"

# 구름 허용 한계치 (0.0 ~ 100.0)
MAX_CC_PERCENT = 10.0

# 추출할 지수 목록
TARGET_INDICES = ["RGB", "NDVI", "NDMI", "GNDVI", "OSAVI", "NDRE", "LCI"]


# =============================================================================
# [2] 파일 불러오기 (ZIP 지원) 및 좌표계(CRS) 자동 변환 함수
# =============================================================================
def get_bbox_from_file(file_path):
    print(f"   📂 공간 데이터 로드 중: {os.path.basename(file_path)}")

    if file_path.lower().endswith('.zip'):
        read_path = f"zip://{file_path}"
    else:
        read_path = file_path

    gdf = gpd.read_file(read_path)
    current_crs = gdf.crs

    # [보정 핵심 1] 위경도(4326)가 아닌 평면 미터 좌표계(3857)로 강제 변환
    if current_crs is None or current_crs.to_epsg() != 3857:
        print("   🔄 미터 단위 평면 좌표계(EPSG:3857)로 변환 중...")
        gdf = gdf.to_crs(epsg=3857)

    bounds = gdf.total_bounds
    return bounds.tolist()


# =============================================================================
# [3] 초기화 및 유틸리티 설정
# =============================================================================
config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

if not os.path.exists(AOI_FOLDER_PATH):
    os.makedirs(AOI_FOLDER_PATH)
    print(f"⚠️ '{AOI_FOLDER_PATH}' 폴더를 생성했습니다. 여기에 .zip, .shp, .geojson 파일을 넣어주세요.")

# =============================================================================
# [4] Evalscript (Production용: 안전 모드)
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
  var val_lci = calcIndex(b08, b04, b05); 

  var osavi_denom = b08 + b04 + 0.16;
  var val_osavi = (osavi_denom === 0) ? 0 : (1.16 * (b08 - b04)) / osavi_denom;
  var val_rgb = [b04 * 2.5, b03 * 2.5, b02 * 2.5];

  return {
    RGB: val_rgb, NDVI: [val_ndvi], NDMI: [val_ndmi],
    GNDVI: [val_gndvi], OSAVI: [val_osavi], NDRE: [val_ndre], LCI: [val_lci]
  };
}

function calcIndex(nir, other, other2) {
    if (other2 !== undefined) { 
        return (nir + other === 0) ? 0 : (nir - other2) / (nir + other);
    }
    return (nir + other === 0) ? 0 : (nir - other) / (nir + other);
}

function createZero() {
    return { RGB: [0,0,0], NDVI: [0], NDMI: [0], GNDVI: [0], OSAVI: [0], NDRE: [0], LCI: [0] };
}
"""

# =============================================================================
# [5] 다중 POI 자동 수집 루프 (Core Logic)
# =============================================================================
supported_extensions = ('.zip', '.geojson', '.shp')
poi_files = [f for f in os.listdir(AOI_FOLDER_PATH) if f.lower().endswith(supported_extensions)]

if not poi_files:
    print(f"\n❌ '{AOI_FOLDER_PATH}' 폴더에 처리할 공간 데이터 파일(.zip, .geojson, .shp)이 없습니다.")
    exit()

print(f"\n🎯 총 {len(poi_files)}개의 관심 지역(POI) 파일을 찾았습니다.")

for poi_idx, file_name in enumerate(poi_files):
    farm_id = os.path.splitext(file_name)[0]
    file_path = os.path.join(AOI_FOLDER_PATH, file_name)

    print(f"\n{'=' * 60}")
    print(f"🌾 [{poi_idx + 1}/{len(poi_files)}] 대상지 처리 시작: {farm_id}")
    print(f"{'=' * 60}")

    try:
        # 5.1 공간 데이터에서 BBox 추출
        raw_bbox = get_bbox_from_file(file_path)
        min_lon, max_lon = min(raw_bbox[0], raw_bbox[2]), max(raw_bbox[0], raw_bbox[2])
        min_lat, max_lat = min(raw_bbox[1], raw_bbox[3]), max(raw_bbox[1], raw_bbox[3])

        # [보정 핵심 2] CRS.WGS84 대신 CRS.POP_WEB (Sentinel Hub의 3857 명칭) 사용
        farm_bbox = BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.POP_WEB)

        # 이제 해상도 10이 완벽한 10m x 10m 정사각형 픽셀을 의미하게 됩니다.
        farm_size = bbox_to_dimensions(farm_bbox, resolution=10)

        # 5.2 Catalog 검색
        print(f"\n   🔍 {farm_id} 주변 위성 촬영 목록 조회 중... ({START_DATE} ~ {END_DATE})")
        catalog = SentinelHubCatalog(config=config)
        search_iterator = catalog.search(
            collection=DataCollection.SENTINEL2_L2A,
            time=(START_DATE, END_DATE),
            bbox=farm_bbox,
            fields={"include": ["id", "properties.datetime", "properties.eo:cloud_cover"], "exclude": []}
        )

        valid_dates = []
        for feature in search_iterator:
            obs_date_str = feature["properties"]["datetime"]
            cloud_cover = feature["properties"]["eo:cloud_cover"]

            if cloud_cover <= MAX_CC_PERCENT:
                dt_obj = datetime.datetime.fromisoformat(obs_date_str.replace('Z', '+00:00'))
                date_str = dt_obj.strftime("%Y-%m-%d")
                time_str = dt_obj.strftime("%H:%M:%S")

                if date_str not in [d['date'] for d in valid_dates]:
                    valid_dates.append({'date': date_str, 'time': time_str, 'cloud': cloud_cover})

        valid_dates.sort(key=lambda x: x['date'])

        if not valid_dates:
            print(f"   ⚠️ {farm_id}에 대해 구름 {MAX_CC_PERCENT}% 이하인 맑은 날짜를 찾지 못했습니다.")
            continue

        print(f"   ✅ 총 {len(valid_dates)}개의 유효한 촬영 날짜 발견.")

        # 5.3 날짜별 다운로드 실행
        for d_idx, item in enumerate(valid_dates):
            target_date = item['date']
            print(f"\n   🚀 [{d_idx + 1}/{len(valid_dates)}] 다운로드: {target_date} {item['time']} UTC")

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

            # 다운로드 및 압축 해제 처리
            data = request.get_data(save_data=True)
            saved_paths = request.get_filename_list()

            relative_tar_path = saved_paths[0]
            tar_path = relative_tar_path if os.path.exists(relative_tar_path) else os.path.join(OUTPUT_FOLDER,
                                                                                                relative_tar_path)

            if tar_path.endswith('.tar') and os.path.exists(tar_path):
                folder_path = os.path.dirname(tar_path)

                with tarfile.open(tar_path) as tar:
                    tar.extractall(path=folder_path, filter='data')

                date_clean = target_date.replace("-", "")

                for identifier in TARGET_INDICES:
                    old_name = f"{identifier}.tif"
                    old_file_path = os.path.join(folder_path, old_name)
                    new_name = f"{date_clean}_{farm_id}_{identifier}.tif"
                    new_file_path = os.path.join(folder_path, new_name)

                    if os.path.exists(old_file_path):
                        if os.path.exists(new_file_path):
                            os.remove(new_file_path)
                        os.rename(old_file_path, new_file_path)

                os.remove(tar_path)
                print(f"      ✅ 처리 완료: {date_clean} 데이터 저장됨.")

            else:
                print(f"      ⚠️ 경고: 압축 파일이 발견되지 않았습니다.")

    except Exception as e:
        print(f"\n   ❌ {farm_id} 처리 중 오류 발생: {e}")

print(f"\n🎉 모든 POI 대상지의 시계열 데이터 수집이 완료되었습니다! ('{OUTPUT_FOLDER}' 확인)")