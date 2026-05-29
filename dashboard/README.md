# Marketing Crawler Dashboard

Google Sheet에 저장된 6개 통신 사이트 크롤링 데이터를 Next.js 대시보드로 보여주고,
OpenAI 기반 AI 채팅으로 최신 데이터를 질문할 수 있는 웹 앱입니다.

## 구성

- `app/api/dashboard`: Google Sheet 데이터를 읽어서 차트/테이블용 JSON으로 변환
- `app/api/chat`: Google Sheet 최신 요약을 시스템 프롬프트에 넣고 OpenAI로 답변 생성
- `components/GiftTrendChart`: Recharts 사은품 추이 차트
- `components/DataTable`: 최신 크롤링 데이터 테이블
- `components/ChatPanel`: 실시간 스트리밍 AI 채팅 UI

## 1. Node.js 설치

현재 PC에서는 Cursor 내부 Node만 잡히고 `npm` 명령이 없는 상태일 수 있습니다.
아래 사이트에서 Node.js LTS 버전을 설치해 주세요.

```text
https://nodejs.org
```

설치 후 새 PowerShell을 열고 확인합니다.

```powershell
node --version
npm --version
```

## 2. 패키지 설치

프로젝트 루트에서 아래 명령을 실행합니다.

```powershell
cd "C:\Users\warin\OneDrive\바탕 화면\MONITORING AGENT\dashboard"
npm install
```

## 3. 환경 변수 설정

`.env.local.example` 파일을 복사해서 `.env.local` 파일을 만듭니다.

```powershell
Copy-Item .env.local.example .env.local
```

`.env.local`에서 `OPENAI_API_KEY`에 본인의 OpenAI API 키를 입력합니다.

```text
OPENAI_API_KEY=sk-...
```

Google Sheet 인증 파일은 기본적으로 부모 폴더의 기존 서비스 계정 파일을 사용합니다.

```text
GOOGLE_APPLICATION_CREDENTIALS=../site-monitoriing-project-c639a6c0fe66.json
```

Google Drive에서 시트 이름으로 못 찾는 경우에는 `GOOGLE_SPREADSHEET_ID`에 시트 ID를 넣으면 됩니다.

## 4. 개발 서버 실행

```powershell
npm run dev
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:3000
```

## 5. AI 채팅 예시 질문

- 오늘 가장 사은품이 높은 통신사는 어디야?
- SKB와 SKT 중 어떤 사이트의 혜택이 더 좋아?
- 오늘 마케팅팀이 봐야 할 핵심 변동 사항을 요약해줘.
- 인터넷 단독 상품 중 사은품이 가장 높은 상품을 찾아줘.

## 주의

- 이 앱은 기존 Python 크롤러를 수정하지 않습니다.
- 대시보드는 Google Sheet에 저장된 데이터를 읽기만 합니다.
- AI 답변은 `/api/chat`에서 Google Sheet 최신 요약을 숨겨진 시스템 메시지로 함께 전달해 생성합니다.
