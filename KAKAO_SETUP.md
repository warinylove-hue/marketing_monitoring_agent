# 카카오톡 알림 설정 방법

`daily_crawl_with_kakao.py`는 매일 크롤링 진행 상황을 카카오톡 "나에게 보내기"로 보낼 수 있습니다.
아래 설정을 한 번만 완료하면 됩니다.

## 1. Kakao Developers 앱 만들기

1. https://developers.kakao.com 에 로그인합니다.
2. `내 애플리케이션` > `애플리케이션 추가하기`를 누릅니다.
3. 앱 이름을 예: `마케팅 크롤링 알림`으로 만듭니다.
4. 앱 화면에서 `앱 키` > `REST API 키`를 복사합니다.

## 2. 카카오 로그인 Redirect URI 등록

1. 만든 앱에서 `카카오 로그인` 메뉴로 이동합니다.
2. `활성화 설정`을 `ON`으로 바꿉니다.
3. `Redirect URI`에 아래 주소를 추가합니다.

```text
http://localhost:3000
```

## 3. 동의 항목 설정

1. `카카오 로그인` > `동의항목`으로 이동합니다.
2. `카카오톡 메시지 전송` 권한을 설정합니다.
3. 권한 이름은 보통 `talk_message`입니다.

## 4. 토큰 발급

아래 주소에서 `REST_API_KEY` 부분을 본인의 REST API 키로 바꾼 뒤 브라우저 주소창에 붙여넣습니다.

```text
https://kauth.kakao.com/oauth/authorize?client_id=REST_API_KEY&redirect_uri=http://localhost:3000&response_type=code&scope=talk_message
```

로그인/동의 후 브라우저 주소가 `http://localhost:3000/?code=...` 형태로 바뀝니다.
주소창의 `code=` 뒤 값을 복사합니다.

그 다음 PowerShell에서 아래 명령을 실행합니다.
`REST_API_KEY`와 `복사한_CODE`를 실제 값으로 바꿔 주세요.

```powershell
$body = @{
  grant_type = "authorization_code"
  client_id = "REST_API_KEY"
  redirect_uri = "http://localhost:3000"
  code = "복사한_CODE"
}
Invoke-RestMethod -Method Post -Uri "https://kauth.kakao.com/oauth/token" -Body $body
```

출력 결과에서 `access_token`과 `refresh_token`을 복사합니다.

## 5. kakao_config.json 만들기

`kakao_config.example.json` 파일을 복사해서 같은 폴더에 `kakao_config.json` 이름으로 만듭니다.
그리고 아래처럼 실제 값을 입력합니다.

```json
{
  "rest_api_key": "실제 REST API 키",
  "access_token": "실제 access_token",
  "refresh_token": "실제 refresh_token"
}
```

`kakao_config.json`에는 개인 토큰이 들어 있으므로 외부에 공유하지 마세요.

## 6. 알림 테스트

설정 후 PowerShell에서 아래 명령으로 전체 크롤링을 직접 실행해 볼 수 있습니다.

```powershell
python daily_crawl_with_kakao.py
```

정상 설정이면 카카오톡으로 시작/사이트별 완료/전체 완료 메시지가 옵니다.
