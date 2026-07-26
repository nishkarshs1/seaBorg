import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { useStore } from "@/store";
import { sendChat, stopChat } from "@/lib/chat";

export function Composer() {
  const [value, setValue] = useState("");
  const pending = useStore((s) => s.pending);
  const hasMessages = useStore((s) => s.messages.length > 0);

  async function send(text: string) {
    if (!text.trim()) return;
    setValue("");
    await sendChat(text);
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (pending) {
      stopChat();
    } else {
      send(value);
    }
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!pending) {
        send(value);
      }
    }
  };

  return (
    <div className="border-t border-[var(--glass-border)] bg-transparent p-4">
      <form
        onSubmit={onSubmit}
        className="flex items-end gap-2 rounded-xl border border-[var(--glass-border)] bg-white/[0.02] p-2 focus-within:border-teal/40"
      >
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKey}
          rows={1}
          placeholder="Ask about temperatures, salinity, depth profiles…"
          className="min-h-[40px] max-h-32 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground"
        />
        {pending ? (
          <button
            type="button"
            onClick={stopChat}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-white transition-opacity hover:opacity-90 cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #ef4444 0%, #ff5577 100%)",
            }}
            aria-label="Stop"
          >
            <Square className="h-3.5 w-3.5 fill-white" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!value.trim()}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-primary-foreground transition-opacity disabled:opacity-40 cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #00d4aa 0%, #00a8ff 100%)",
            }}
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </form>
    </div>
  );
}
