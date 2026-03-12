import os
import urllib3
import requests
from sentinelhub import SHConfig, SentinelHubSession

# =======================================================================
# [보안 우회 설정] 사내 보안 프로그램으로 인한 SSL 인증 에러 무시
# =======================================================================
# 1. InsecureRequestWarning 경고 메시지 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2. requests 라이브러리의 모든 통신에서 SSL 검사(verify=False) 강제 적용
old_request = requests.Session.request
def new_request(self, method, url, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, **kwargs)
requests.Session.request = new_request
# =======================================================================

# 1. 설정 인스턴스 생성
config = SHConfig()

# 2. 발급받은 키 입력 (새로 발급받은 키 사용)
config.sh_client_id = '6ca4716a-2747-4773-88fe-6f92aa0cc38c'
config.sh_client_secret = 'tI5weoZEdReDwFLdoYBSntphmadjJbNc'

# 3. 설정 저장
config.save()

print("설정이 완료되었습니다! 현재 설정된 인스턴스 ID:", config.instance_id)
print("Client ID 설정 확인:", config.sh_client_id)

try:
    # 세션을 열어 토큰을 요청해 봅니다.
    session = SentinelHubSession(config=config)
    token = session.token
    print("✅ 인증 성공! Access Token을 획득했습니다.")
    print(f"Token (앞 20자): {token['access_token'][:20]}...")
except Exception as e:
    print("\n❌ 인증 실패. 에러 메시지를 확인해주세요.")
    print(f"상세 에러: {e}")