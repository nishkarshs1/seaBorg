import { motion } from "framer-motion";
import { Bot, Check, Copy, User } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import type { ChatMessage } from "@/store";
import { SqlAccordion } from "./SqlAccordion";
import { cn } from "@/lib/utils";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("Copied");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copy failed");
    }
  };
  return (
    <button
      onClick={onCopy}
      aria-label="Copy message"
      className="inline-flex items-center gap-1 rounded-md border border-[var(--glass-border)] bg-white/[0.03] px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground transition hover:text-foreground hover:border-teal/40"
    >
      {copied ? <Check className="h-3 w-3 text-teal" /> : <Copy className="h-3 w-3" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const copyText = isUser ? msg.text : msg.payload.answer;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("group flex gap-3", isUser ? "flex-row-reverse" : "")}
    >
      <div
        className={cn(
          "grid h-8 w-8 shrink-0 place-items-center rounded-full border",
          isUser ? "border-teal/25 bg-teal/10" : "border-[var(--glass-border)] bg-card",
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-teal" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-ocean" />
        )}
      </div>

      <div className={cn("max-w-[85%] flex flex-col", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed border",
            isUser
              ? "border-teal/20 bg-gradient-to-br from-teal/15 to-ocean/10 text-foreground"
              : "glass border-[var(--glass-border)]",
          )}
        >
          {msg.role === "user" ? (
            <p>{msg.text}</p>
          ) : (
            <>
              <p className="whitespace-pre-wrap">{msg.payload.answer}</p>
              <SqlAccordion sqlText={msg.payload.sql_used} />
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                <span className="rounded-full border border-[var(--glass-border)] px-2 py-0.5 font-mono uppercase tracking-wider">
                  {msg.payload.chart_type}
                </span>
                <span className="font-mono">{msg.payload.data.length} rows</span>
                {msg.payload.float_ids && msg.payload.float_ids.length > 0 && (
                  <span className="font-mono">{msg.payload.float_ids.length} floats</span>
                )}
              </div>
            </>
          )}
        </div>
        <div
          className={cn(
            "mt-1.5 flex opacity-0 transition-opacity group-hover:opacity-100",
            isUser ? "justify-end" : "justify-start",
          )}
        >
          <CopyButton text={copyText} />
        </div>
      </div>
    </motion.div>
  );
}
