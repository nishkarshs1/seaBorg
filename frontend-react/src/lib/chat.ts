import { postChat } from "./api";
import { useStore } from "@/store";

export async function sendChat(text: string) {
  const t = text.trim();
  const { pending, addUser, addAi, setPending, selectedOcean } = useStore.getState();
  if (!t || pending) return;

  const messages = useStore.getState().messages;
  const history = messages.slice(-10).map((m) => ({
    role: m.role,
    text: m.role === "user" ? m.text : m.payload.answer,
  }));

  addUser(t);
  setPending(true);
  try {
    const res = await postChat(t, selectedOcean, history);
    addAi(res);
  } finally {
    useStore.getState().setPending(false);
  }
}

export const suggestedQueries = [
  { emoji: "🌡️", text: "What is the average ocean temperature at 500m depth?" },
  { emoji: "📍", text: "Which ARGO float is closest to the equator?" },
  { emoji: "📈", text: "Show the salinity trend over the last 5 years" },
  { emoji: "🌊", text: "Give me the temperature profile comparison for Float 1900121" },
  { emoji: "📅", text: "What was the deepest dive recorded in 2024?" },
];
