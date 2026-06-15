# Cloud Run Jobs 배포 준비

이 문서는 로컬 Python 크롤러를 Google Cloud Run Jobs에서 실행하기 위한 1차 준비 안내입니다.

## 준비할 Google Cloud 서비스

- Cloud Run
- Cloud Scheduler
- Secret Manager
- Artifact Registry
- Cloud Build

## 로컬에서 한 번만 준비

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

## Secret Manager에 넣을 값

### Google 서비스 계정 JSON

기존 `site-monitoriing-project-c639a6c0fe66.json` 파일을 Secret Manager에 저장합니다.

```powershell
gcloud secrets create google-sheets-credentials --data-file="site-monitoriing-project-c639a6c0fe66.json"
```

Cloud Run Job에서는 이 Secret을 파일로 마운트하고 아래 환경변수를 지정합니다.

```text
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/credentials.json
```

### Kakao 설정

`kakao_config.json` 전체를 Secret으로 저장하는 방식이 가장 간단합니다.

```powershell
gcloud secrets create kakao-config --data-file="kakao_config.json"
```

Cloud Run Job에서는 이 Secret을 파일로 마운트하고 아래 환경변수를 지정합니다.

```text
KAKAO_CONFIG_FILE=/secrets/kakao/kakao_config.json
```

## Docker 이미지 빌드

아래 `REGION`은 예: `asia-northeast3` 또는 `asia-northeast1`을 사용합니다.

```powershell
gcloud artifacts repositories create crawler-repo --repository-format=docker --location=asia-northeast3
gcloud builds submit --tag asia-northeast3-docker.pkg.dev/YOUR_PROJECT_ID/crawler-repo/marketing-crawler:latest
```

## Cloud Run Job 생성 예시

```powershell
gcloud run jobs create marketing-crawler-job `
  --image asia-northeast3-docker.pkg.dev/YOUR_PROJECT_ID/crawler-repo/marketing-crawler:latest `
  --region asia-northeast3 `
  --cpu 2 `
  --memory 4Gi `
  --task-timeout 3600 `
  --set-env-vars PYTHONIOENCODING=utf-8,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google/credentials.json,KAKAO_CONFIG_FILE=/secrets/kakao/kakao_config.json `
  --set-secrets /secrets/google/credentials.json=google-sheets-credentials:latest,/secrets/kakao/kakao_config.json=kakao-config:latest
```

## 수동 실행

```powershell
gcloud run jobs execute marketing-crawler-job --region asia-northeast3 --wait
```

## 매일 오전 8시 예약

Cloud Scheduler는 다음 단계에서 연결합니다. 시간대는 `Asia/Seoul`, 스케줄은 `0 8 * * *`를 사용합니다.

