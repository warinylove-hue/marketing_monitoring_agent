import { spawn, type ChildProcess } from "node:child_process";
import { createWriteStream, existsSync, mkdirSync } from "node:fs";
import path from "node:path";

import { google } from "googleapis";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type CrawlState = {
  process: ChildProcess | null;
  startedAt: string;
  logFile: string;
};

declare global {
  // eslint-disable-next-line no-var
  var manualCrawlState: CrawlState | undefined;
}

function getCrawlerPaths() {
  const projectRoot = path.resolve(process.cwd(), "..");
  const scriptPath = path.join(projectRoot, "daily_crawl_with_kakao.py");
  const logDir = path.join(projectRoot, "logs");
  return { projectRoot, scriptPath, logDir };
}

function hasCloudRunJobConfig() {
  return Boolean(
    process.env.GOOGLE_CLOUD_PROJECT_ID &&
      process.env.CLOUD_RUN_REGION &&
      process.env.CLOUD_RUN_JOB_NAME,
  );
}

async function runCloudRunJob() {
  const serviceAccountEmail =
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL || process.env.GOOGLE_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");

  if (!serviceAccountEmail || !privateKey) {
    return NextResponse.json(
      {
        error:
          "Cloud Run Job 실행에 필요한 GOOGLE_SERVICE_ACCOUNT_EMAIL 또는 GOOGLE_PRIVATE_KEY가 없습니다.",
      },
      { status: 500 },
    );
  }

  const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID!;
  const region = process.env.CLOUD_RUN_REGION!;
  const jobName = process.env.CLOUD_RUN_JOB_NAME!;
  const auth = new google.auth.GoogleAuth({
    credentials: {
      client_email: serviceAccountEmail,
      private_key: privateKey,
    },
    scopes: ["https://www.googleapis.com/auth/cloud-platform"],
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();

  const response = await fetch(
    `https://${region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${projectId}/jobs/${jobName}:run`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token.token}`,
        "Content-Type": "application/json",
      },
      body: "{}",
    },
  );

  const payloadText = await response.text();
  if (!response.ok) {
    return NextResponse.json(
      {
        error: "Cloud Run Job 실행 요청에 실패했습니다.",
        detail: payloadText,
      },
      { status: response.status },
    );
  }

  let executionName = "";
  try {
    const payload = JSON.parse(payloadText) as { metadata?: { name?: string } };
    executionName = payload.metadata?.name || "";
  } catch {
    executionName = "";
  }

  return NextResponse.json({
    ok: true,
    message:
      "클라우드 크롤러 실행을 요청했습니다. 완료 후 '최신 저장된 정보 불러오기'를 눌러 화면에 반영하세요.",
    executionName,
  });
}

export async function GET() {
  const state = globalThis.manualCrawlState;
  return NextResponse.json({
    running: Boolean(state?.process && !state.process.killed),
    startedAt: state?.startedAt || "",
    logFile: state?.logFile || "",
  });
}

export async function POST() {
  if (hasCloudRunJobConfig()) {
    return runCloudRunJob();
  }

  if (process.env.VERCEL === "1" && !process.env.CLOUD_CRAWLER_TRIGGER_URL) {
    return NextResponse.json(
      {
        message:
          "웹 배포 버전에서는 2단계에서 Cloud Run 크롤러를 연결한 뒤 사용할 수 있습니다. 현재는 로컬 개발 환경에서만 즉시 수집이 가능합니다.",
      },
      { status: 501 },
    );
  }

  if (process.env.CLOUD_CRAWLER_TRIGGER_URL) {
    const response = await fetch(process.env.CLOUD_CRAWLER_TRIGGER_URL, {
      method: "POST",
      headers: process.env.CLOUD_CRAWLER_TRIGGER_TOKEN
        ? { Authorization: `Bearer ${process.env.CLOUD_CRAWLER_TRIGGER_TOKEN}` }
        : undefined,
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "클라우드 크롤러 실행 요청에 실패했습니다." },
        { status: response.status },
      );
    }

    return NextResponse.json({
      ok: true,
      message: "클라우드 크롤러 실행을 요청했습니다.",
    });
  }

  const current = globalThis.manualCrawlState;
  if (current?.process && !current.process.killed) {
    return NextResponse.json(
      {
        error: "이미 자료 수집이 실행 중입니다. 완료 후 다시 실행해 주세요.",
        startedAt: current.startedAt,
        logFile: current.logFile,
      },
      { status: 409 },
    );
  }

  const { projectRoot, scriptPath, logDir } = getCrawlerPaths();
  if (!existsSync(scriptPath)) {
    return NextResponse.json(
      { error: `크롤러 파일을 찾지 못했습니다: ${scriptPath}` },
      { status: 500 },
    );
  }

  mkdirSync(logDir, { recursive: true });
  const startedAt = new Date().toISOString();
  const logFile = path.join(logDir, `manual-crawl-${startedAt.replace(/[:.]/g, "-")}.log`);
  const logStream = createWriteStream(logFile, { flags: "a" });
  const pythonExe = process.env.CRAWLER_PYTHON || "python";

  const child = spawn(pythonExe, ["daily_crawl_with_kakao.py"], {
    cwd: projectRoot,
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
    },
    shell: process.platform === "win32",
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout?.pipe(logStream);
  child.stderr?.pipe(logStream);
  child.on("exit", () => {
    logStream.end();
    globalThis.manualCrawlState = undefined;
  });

  globalThis.manualCrawlState = {
    process: child,
    startedAt,
    logFile,
  };

  return NextResponse.json({
    ok: true,
    message: "자료 수집을 시작했습니다.",
    pid: child.pid,
    startedAt,
    logFile,
  });
}
