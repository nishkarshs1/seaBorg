import { useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";
import { useStore } from "@/store";
import { MessageBubble } from "./MessageBubble";
import { sendChat, suggestedQueries } from "@/lib/chat";

export function MessageList() {
  const messages = useStore((s) => s.messages);
  const pending = useStore((s) => s.pending);
  const ref = useRef<HTMLDivElement>(null);

  // Track the length of the last AI answer for auto-scroll during streaming.
  // Always a number (0 if no AI message) so the useEffect dependency array is stable.
  const lastMsg = messages.length > 0 ? messages[messages.length - 1] : null;
  const lastAnswerLen = lastMsg && lastMsg.role === "ai" ? lastMsg.payload.answer.length : 0;

  // Auto-scroll to bottom when new messages appear OR when streaming text grows
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, lastAnswerLen]);

  return (
    <div ref={ref} className="flex-1 space-y-5 overflow-y-auto px-5 py-6">
      {messages.length === 0 && (
        <div className="grid h-full place-items-center text-center">
          <div className="max-w-xl">
            <div
              className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl"
              style={{
                background: "linear-gradient(135deg, rgba(0,212,170,0.15), rgba(0,168,255,0.15))",
                border: "1px solid rgba(0,212,170,0.3)",
              }}
            >
              <Sparkles className="h-6 w-6 text-teal" />
            </div>
            <h3 className="text-lg font-semibold">Ask the ocean</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Query 694,182 ARGO float readings in plain English. SeaBorg generates SQL, fetches the
              rows, and visualizes the answer.
            </p>
            <div className="mt-6">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Try a suggested query
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {suggestedQueries.map((s) => (
                  <button
                    key={s.text}
                    onClick={() => sendChat(s.text)}
                    disabled={pending}
                    className="group rounded-full border border-[var(--glass-border)] bg-white/[0.03] px-3 py-1.5 text-xs text-foreground/85 transition-all hover:border-teal/50 hover:bg-white/[0.06] hover:text-foreground disabled:opacity-50"
                  >
                    <span className="mr-1.5">{s.emoji}</span>
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {messages.map((m, i) => (
        <MessageBubble key={m.id} msg={m} isLast={i === messages.length - 1} />
      ))}
    </div>
  );
}
