import { getDashboardData } from "@/lib/dashboardData";
import type { ChatMessage } from "@/types/dashboard";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type OpenAIChunk = {
  choices?: Array<{
    delta?: {
      content?: string;
    };
  }>;
};

export async function POST(request: Request) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return new Response("OPENAI_API_KEY가 .env.local에 설정되어 있지 않습니다.", {
      status: 500,
    });
  }

  const { messages = [] } = (await request.json()) as { messages: ChatMessage[] };
  const safeMessages = messages
    .filter(
      (message) =>
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        message.content.trim(),
    )
    .slice(-10);

  const dashboardData = await getDashboardData();

  const systemPrompt = [
    "너는 통신 가입 비교 시장을 분석하는 한국어 AI 데이터 애널리스트다.",
    "사용자는 마케팅 임원이며 코딩 지식이 없으므로, 답변은 비즈니스 관점으로 명확하고 짧게 작성한다.",
    "반드시 아래 [Google Sheet 최신 데이터 요약]을 근거로 답한다.",
    "데이터에 없는 사실, 외부 사이트의 현재 상황, 미래 금액은 추측하지 않는다.",
    "금액은 사용자가 이해하기 쉽게 원/만원 단위로 표현하고, 가능하면 사이트명과 상품 조합을 함께 말한다.",
    "질문이 '오늘'을 언급하면 최신 수집일 데이터를 기준으로 해석한다.",
    "질문이 '25일', '28일'처럼 일자만 언급하면 [날짜별 비교 요약]에 있는 YYYY-MM-DD 중 같은 일자의 데이터를 찾아 비교한다.",
    "데이터가 비어 있거나 특정 사이트 데이터가 없으면 그 한계를 먼저 말한다.",
    "",
    "[Google Sheet 최신 데이터 요약]",
    dashboardData.aiSummary,
  ].join("\n");

  const openAiResponse = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
      stream: true,
      temperature: 0.2,
      messages: [
        { role: "system", content: systemPrompt },
        ...safeMessages.map((message) => ({
          role: message.role,
          content: message.content,
        })),
      ],
    }),
  });

  if (!openAiResponse.ok || !openAiResponse.body) {
    const errorText = await openAiResponse.text();
    return new Response(errorText || "OpenAI 응답 오류", {
      status: openAiResponse.status,
    });
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const stream = new ReadableStream({
    async start(controller) {
      const reader = openAiResponse.body!.getReader();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const payload = trimmed.replace(/^data:\s*/, "");
          if (payload === "[DONE]") {
            controller.close();
            return;
          }

          try {
            const chunk = JSON.parse(payload) as OpenAIChunk;
            const content = chunk.choices?.[0]?.delta?.content;
            if (content) controller.enqueue(encoder.encode(content));
          } catch {
            // Ignore malformed keep-alive chunks.
          }
        }
      }

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache",
    },
  });
}
