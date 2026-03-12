import os
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
CLIENT_ID = '6ca4716a-2747-4773-88fe-6f92aa0cc38c'
CLIENT_SECRET = 'tI5weoZEdReDwFLdoYBSntphmadjJbNc'  # ★ 반드시 수정하세요!

OUTPUT_FOLDER = 'sentinel_timeseries_data'
AOI_FOLDER_PATH = 'aoi'

START_DATE = "2026-01-01"
END_DATE = "2026-03-31"
MAX_CC_PERCENT = 10

TARGET_INDICES = ["RGB", "NDVI", "NDMI", "GNDVI", "OSAVI", "NDRE", "LCI"]


# =============================================================================
# [2] 파일 불러오기 및 위성 원본 좌표계(UTM) 자동 계산/변환 함수
# =============================================================================
def get_bbox_from_file(file_path):
    print(f"   📂 공간 데이터 로드 중: {os.path.basename(file_path)}")

    if file_path.lower().endswith('.zip'):
        read_path = f"zip://{file_path}"
    else:
        read_path = file_path

    gdf = gpd.read_file(read_path)

    # 1. 중심 경도를 구하기 위해 임시로 WGS84 변환
    gdf_wgs = gdf.to_crs(epsg=4326)

    # [경고 해결] centroid 함수 대신 BBox의 양 끝값을 이용해 중심 경도를 계산합니다.
    min_lon, min_lat, max_lon, max_lat = gdf_wgs.total_bounds
    center_lon = (min_lon + max_lon) / 2.0

    # 2. 해당 위치의 UTM Zone 자동 계산 (한국은 EPSG:32652가 나옵니다)
    utm_zone = int((center_lon + 180) / 6) + 1
    epsg_code = 32600 + utm_zone
    epsg_str = str(epsg_code)

    print(f"   🔄 Pix4D와 동일한 위성 원본 좌표계(EPSG:{epsg_str})로 변환 중...")

    # 3. Shapefile을 UTM 좌표계로 완벽하게 투영
    gdf_utm = gdf.to_crs(epsg=epsg_code)
    bounds = gdf_utm.total_bounds

    # BBox 배열과 EPSG 문자열 반환
    return bounds.tolist(), epsg_str

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

# =============================================================================
# [4] Evalscript
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

  var b02 = sample.B02 || 0, b03 = sample.B03 || 0, b04 = sample.B04 || 0;
  var b05 = sample.B05 || 0, b08 = sample.B08 || 0, b11 = sample.B11 || 0;

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
    if (other2 !== undefined) return (nir + other === 0) ? 0 : (nir - other2) / (nir + other);
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
    print(f"\n❌ '{AOI_FOLDER_PATH}' 폴더에 파일이 없습니다.")
    exit()

for poi_idx, file_name in enumerate(poi_files):
    farm_id = os.path.splitext(file_name)[0]
    file_path = os.path.join(AOI_FOLDER_PATH, file_name)

    print(f"\n{'=' * 60}")
    print(f"🌾 [{poi_idx + 1}/{len(poi_files)}] 대상지 처리 시작: {farm_id}")
    print(f"{'=' * 60}")

    try:
        # [핵심] UTM BBox 좌표와 해당 EPSG 코드 받아오기
        raw_bbox, epsg_str = get_bbox_from_file(file_path)
        min_x, min_y, max_x, max_y = raw_bbox

        # [핵심] 찾아낸 EPSG:32652(또는 해당 지역 UTM)를 도화지로 설정
        farm_bbox = BBox(bbox=[min_x, min_y, max_x, max_y], crs=CRS(epsg_str))

        # 10m 단위 완벽한 정사각형 픽셀 해상도
        farm_size = bbox_to_dimensions(farm_bbox, resolution=10)

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
            print(f"   ⚠️ 맑은 날짜가 없습니다.")
            continue

        for d_idx, item in enumerate(valid_dates):
            target_date = item['date']
            print(f"\n   🚀 [{d_idx + 1}/{len(valid_dates)}] 다운로드: {target_date}")

            request = SentinelHubRequest(
                evalscript=EVALSCRIPT,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=(target_date, target_date),
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
                    old_file_path = os.path.join(folder_path, f"{identifier}.tif")
                    new_file_path = os.path.join(folder_path, f"{date_clean}_{farm_id}_{identifier}.tif")
                    if os.path.exists(old_file_path):
                        if os.path.exists(new_file_path): os.remove(new_file_path)
                        os.rename(old_file_path, new_file_path)

                os.remove(tar_path)
                print(f"      ✅ 완료: {date_clean}")

    except Exception as e:
        print(f"\n   ❌ 처리 중 오류 발생: {e}")

print(f"\n🎉 시계열 데이터 수집이 완료되었습니다!")