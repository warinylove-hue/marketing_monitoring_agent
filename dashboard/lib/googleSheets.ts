import path from "node:path";

import { google } from "googleapis";

const SHEET_NAMES = ["아정당", "MISO", "U+", "KT", "SKB", "SKT"];
const DEFAULT_SPREADSHEET_NAME = "마케팅_크롤링_DB";
const DEFAULT_CREDENTIALS_PATH = "../site-monitoriing-project-c639a6c0fe66.json";
const GOOGLE_SCOPES = [
  "https://www.googleapis.com/auth/spreadsheets.readonly",
  "https://www.googleapis.com/auth/drive.metadata.readonly",
];

function quoteSheetName(name: string): string {
  return `'${name.replace(/'/g, "''")}'!A:G`;
}

async function getAuth() {
  const serviceAccountEmail =
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL || process.env.GOOGLE_CLIENT_EMAIL;
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");

  if (serviceAccountEmail && privateKey) {
    return new google.auth.GoogleAuth({
      credentials: {
        client_email: serviceAccountEmail,
        private_key: privateKey,
      },
      scopes: GOOGLE_SCOPES,
    });
  }

  const credentialsPath = path.resolve(
    process.cwd(),
    process.env.GOOGLE_APPLICATION_CREDENTIALS || DEFAULT_CREDENTIALS_PATH,
  );

  return new google.auth.GoogleAuth({
    keyFile: credentialsPath,
    scopes: GOOGLE_SCOPES,
  });
}

async function resolveSpreadsheetId(auth: Awaited<ReturnType<typeof getAuth>>) {
  if (process.env.GOOGLE_SPREADSHEET_ID) {
    return process.env.GOOGLE_SPREADSHEET_ID;
  }

  const drive = google.drive({ version: "v3", auth });
  const spreadsheetName =
    process.env.GOOGLE_SPREADSHEET_NAME || DEFAULT_SPREADSHEET_NAME;
  const response = await drive.files.list({
    q: [
      "mimeType='application/vnd.google-apps.spreadsheet'",
      `name='${spreadsheetName.replace(/'/g, "\\'")}'`,
      "trashed=false",
    ].join(" and "),
    fields: "files(id,name)",
    pageSize: 1,
  });

  const file = response.data.files?.[0];
  if (!file?.id) {
    throw new Error(
      `Google Sheet를 찾을 수 없습니다: ${spreadsheetName}. GOOGLE_SPREADSHEET_ID를 .env.local에 넣어주세요.`,
    );
  }
  return file.id;
}

export async function readMarketingSheets() {
  const auth = await getAuth();
  const spreadsheetId = await resolveSpreadsheetId(auth);
  const sheets = google.sheets({ version: "v4", auth });

  const response = await sheets.spreadsheets.values.batchGet({
    spreadsheetId,
    ranges: SHEET_NAMES.map(quoteSheetName),
    valueRenderOption: "FORMATTED_VALUE",
  });

  return (response.data.valueRanges || []).flatMap((range, rangeIndex) => {
    const sheetName = SHEET_NAMES[rangeIndex];
    const rows = range.values || [];
    return rows.slice(1).map((row) => ({
      sheetName,
      values: row as string[],
    }));
  });
}
