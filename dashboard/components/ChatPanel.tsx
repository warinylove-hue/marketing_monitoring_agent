"use client";

import { FormEvent, useRef, useState } from "react";
import { Bot, Send, Sparkles, StopCircle, UserRound } from "lucide-react";

import type { ChatMessage } from "@/types/dashboard";

const STARTER_QUESTIONS = [
  "오늘 가장 사은품이 높은 상품은 뭐야?",
  "사이트별 최고 조건을 표처럼 요약해줘.",
  "인터넷 단독과 인터넷+TV 중 어디가 더 경쟁적이야?",
  "마케팅 임원이 오늘 봐야 할 포인트 3개만 알려줘.",
];

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "안녕하세요. 저는 Google Sheet 최신 크롤링 데이터를 함께 읽고 답변하는 AI 분석 챗봇입니다. 오늘 최고 사은품, 사이트별 비교, 상품 조합별 인사이트를 물어보세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput("");
    setIsLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        const text = await response.text();
        throw new Error(text || "AI 응답을 불러오지 못했습니다.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setMessages((current) => {
          const copy = [...current];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + chunk };
          return copy;
        });
      }
    } catch (error) {
      setMessages((current) => {
        const copy = [...current];
        copy[copy.length - 1] = {
          role: "assistant",
          content:
            error instanceof Error
              ? `오류가 발생했습니다: ${error.message}`
              : "알 수 없는 오류가 발생했습니다.",
        };
        return copy;
      });
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(input);
  }

  function stopStreaming() {
    abortRef.current?.abort();
    setIsLoading(false);
  }

  return (
    <aside className="flex h-[calc(100vh-2rem)] min-h-[760px] flex-col rounded-[2rem] border border-slate-800 bg-slate-950 shadow-2xl lg:sticky lg:top-4">
      <div className="border-b border-white/10 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500 text-white">
            <Sparkles size={22} />
          </div>
          <div>
            <p className="text-sm font-medium text-blue-200">AI Insight Chat</p>
            <h2 className="text-xl font-black text-white">시트 데이터 기반 AI</h2>
          </div>
        </div>
        <p className="mt-4 rounded-2xl bg-white/10 p-3 text-xs leading-5 text-slate-300">
          질문을 보내면 서버의 `/api/chat`이 최신 Google Sheet 요약을 System Message에
          숨겨서 OpenAI에 함께 전달합니다.
        </p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
        {isLoading ? (
          <div className="flex items-center justify-between rounded-2xl bg-blue-500/10 px-4 py-3 text-sm text-blue-100">
            <span>AI가 최신 시트 데이터를 분석 중입니다...</span>
            <button
              type="button"
              onClick={stopStreaming}
              className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2 py-1 text-xs font-bold hover:bg-white/20"
            >
              <StopCircle size={14} />
              중지
            </button>
          </div>
        ) : null}
      </div>

      <div className="space-y-3 border-t border-white/10 p-5">
        <div className="flex flex-wrap gap-2">
          {STARTER_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => void ask(question)}
              className="rounded-full bg-white/10 px-3 py-2 text-left text-xs font-medium text-slate-200 transition hover:bg-white/20"
            >
              {question}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="예: 오늘 가장 좋은 조건은?"
            className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-white px-4 py-3 text-sm text-slate-950 outline-none ring-blue-400 transition focus:ring-4"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500 text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </aside>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-500 text-white">
          <Bot size={16} />
        </div>
      ) : null}
      <div
        className={`max-w-[85%] whitespace-pre-wrap rounded-3xl px-4 py-3 text-sm leading-6 ${
          isUser
            ? "bg-blue-500 text-white"
            : "bg-white/10 text-slate-100 ring-1 ring-white/10"
        }`}
      >
        {message.content || " "}
      </div>
      {isUser ? (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/10 text-white">
          <UserRound size={16} />
        </div>
      ) : null}
    </div>
  );
}
