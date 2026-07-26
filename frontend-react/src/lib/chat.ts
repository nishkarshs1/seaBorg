import { postChat } from "./api";
import { streamChat } from "./stream";
import { StreamAnimator } from "./stream-animator";
import { useStore } from "@/store";

/**
 * Reference to the active StreamAnimator instance.
 * Stored here so that stopChat() can flush remaining buffered text
 * before aborting the network request.
 */
let activeAnimator: StreamAnimator | null = null;

/**
 * Triggers the RAG chat execution flow with smooth character animation.
 *
 * Flow:
 *   1. User message → added to store
 *   2. SSE stream starts → metadata (SQL, chart, data) rendered instantly
 *   3. LLM text chunks → pushed into StreamAnimator buffer
 *   4. StreamAnimator → drains buffer char-by-char at 60fps into the store
 *   5. User sees smooth typing effect like ChatGPT
 */
export async function sendChat(text: string) {
  const t = text.trim();
  const { pending, addUser, setPending, selectedOcean } = useStore.getState();
  if (!t || pending) return;

  // Retrieve chat history to maintain conversation context (last 10 messages)
  const messages = useStore.getState().messages;
  const history = messages.slice(-10).map((m) => ({
    role: m.role,
    text: m.role === "user" ? m.text : m.payload.answer,
  }));

  // Append user's chat bubble to store
  addUser(t);
  setPending(true);

  // Create an AbortController instance to support stopping generation midway
  const ac = new AbortController();
  useStore.getState().setAbortController(ac);

  // Track the message ID assigned to the AI response bubble
  let currentMessageId = "";

  // Create the StreamAnimator that will smoothly render text char-by-char.
  // The onRender callback appends each small text slice to the AI message bubble.
  const animator = new StreamAnimator(
    (slice) => {
      if (currentMessageId) {
        useStore.getState().appendAiAnswer(currentMessageId, slice);
      }
    },
    { charsPerFrame: 3 } // ~180 chars/sec at 60fps — feels natural
  );
  activeAnimator = animator;

  try {
    // Initiate streaming request
    await streamChat(
      t,
      selectedOcean,
      history,
      ac.signal,

      // onMeta: Called when initial SQL, chart type, and rows arrive.
      // Charts and SQL render instantly — no animation needed for metadata.
      (meta) => {
        const id = Math.random().toString(36).slice(2, 10);
        useStore.getState().addAiPlaceholder(id, meta);
        currentMessageId = id;
        return id;
      },

      // onChunk: SSE text token arrives → push into animator buffer (NOT directly into store).
      // The animator will drain it smoothly via requestAnimationFrame.
      (messageId, text) => {
        animator.push(text);
      },

      // onError: Errors are pushed through the animator too so they animate in gracefully
      (messageId, errorText) => {
        animator.push(errorText);
      },

      // onDone: SSE stream is complete. Tell the animator to drain remaining buffer,
      // then cleanup state when the last character has been rendered.
      () => {
        animator.finish(() => {
          activeAnimator = null;
          useStore.getState().setAbortController(null);
          useStore.getState().setPending(false);
        });
      }
    );
  } catch (err) {
    console.error("sendChat error:", err);
    animator.flush(); // Dump any remaining buffer text instantly
    activeAnimator = null;
    useStore.getState().setAbortController(null);
    useStore.getState().setPending(false);
  }
}

/**
 * Stops generation immediately.
 * 1. Flushes any remaining buffered characters into the UI (so partial text isn't lost)
 * 2. Aborts the active fetch/SSE stream
 */
export function stopChat() {
  // Flush remaining animated text so the user keeps what was already generated
  if (activeAnimator) {
    activeAnimator.flush();
    activeAnimator = null;
  }
  useStore.getState().abortActiveStream();
}

export const suggestedQueries = [
  { emoji: "🌡️", text: "What is the average ocean temperature at 500m depth?" },
  { emoji: "📍", text: "Which ARGO float is closest to the equator?" },
  { emoji: "📈", text: "Show the salinity trend over the last 5 years" },
  { emoji: "🌊", text: "Give me the temperature profile comparison for Float 1900121" },
  { emoji: "📅", text: "What was the deepest dive recorded in 2024?" },
];
