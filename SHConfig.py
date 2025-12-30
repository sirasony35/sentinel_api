from sentinelhub import SHConfig

# 1. 설정 인스턴스 생성
config = SHConfig()

# 2. 발급받은 키 입력 (문자열로 입력하세요)
# 주의: 실제 프로젝트에서는 이 키들을 환경 변수(Environment Variable)로 관리하는 것이 보안상 좋습니다.
config.sh_client_id = '2602a8dc-bdc6-4dca-a1eb-9a8a0c9f6b30'
config.sh_client_secret = 'oofByVn5fbUMrkJLWRlZOv29T4EMdHdc'

# 3. 설정 저장 (선택 사항)
# 이 명령어를 한 번 실행하면, 로컬 설정 파일(~/.config/sentinelhub/config.json)에 저장되어
# 다음부터는 ID/Secret 입력 없이 config = SHConfig() 만으로 호출 가능합니다.
config.save()

print("설정이 완료되었습니다! 현재 설정된 인스턴스 ID:", config.instance_id) # instance_id는 없어도 Process API 사용 가능
print("Client ID 설정 확인:", config.sh_client_id)

from sentinelhub import SentinelHubSession

try:
    # 세션을 열어 토큰을 요청해 봅니다.
    session = SentinelHubSession(config=config)
    token = session.token
    print("✅ 인증 성공! Access Token을 획득했습니다.")
    print(f"Token (앞 20자): {token['access_token'][:20]}...")
except Exception as e:
    print("❌ 인증 실패. Client ID와 Secret을 다시 확인해주세요.")
    print(f"에러 메시지: {e}")