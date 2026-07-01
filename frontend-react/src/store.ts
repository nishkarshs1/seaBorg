import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatResponse } from "./lib/mocks";

export type ChatMessage =
  | { id: string; role: "user"; text: string; ts: number }
  | { id: string; role: "ai"; ts: number; payload: ChatResponse };

export type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  ts: number;
};

export type FilterRule = {
  id: string;
  field: "depth" | "temp" | "salinity" | "lat" | "lng" | "id";
  operator: "==" | "!=" | ">" | "<" | ">=" | "<=" | "contains";
  value: string;
};

export type ExplorerFilter = {
  id: string;
  name: string;
  rules: FilterRule[];
  ts: number;
};

type ChatStore = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessage[]; // Backward compatibility: maps to messages of activeSessionId
  pending: boolean;
  sidebarCollapsed: boolean;
  chatSidebarCollapsed: boolean;
  selectedOcean: string;

  theme: "dark" | "light";

  // Explorer Filters State
  explorerFilters: ExplorerFilter[];
  activeFilterId: string | null;
  explorerSidebarCollapsed: boolean;

  addUser: (text: string) => void;
  addAi: (payload: ChatResponse) => void;
  setPending: (v: boolean) => void;
  clear: () => void;
  toggleSidebar: () => void;
  toggleChatSidebar: () => void;
  setSelectedOcean: (ocean: string) => void;
  toggleTheme: () => void;

  // New actions
  createNewSession: () => string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;

  // Explorer Filters Actions
  createExplorerFilter: (name: string, rules: FilterRule[]) => string;
  updateExplorerFilter: (id: string, name: string, rules: FilterRule[]) => void;
  deleteExplorerFilter: (id: string) => void;
  setActiveFilterId: (id: string | null) => void;
  toggleExplorerSidebar: () => void;
};

const id = () => Math.random().toString(36).slice(2, 10);

export const useStore = create<ChatStore>()(
  persist(
    (set) => ({
      sessions: [],
      activeSessionId: null,
      messages: [],
      pending: false,
      sidebarCollapsed: false,
      chatSidebarCollapsed: false,
      selectedOcean: "All Oceans",
      theme: "dark",

      // Explorer Filters initial state
      explorerFilters: [
        {
          id: "f-surface",
          name: "Surface 0–200m",
          rules: [{ id: "r1", field: "depth", operator: "<=", value: "200" }],
          ts: 1,
        },
        {
          id: "f-mid",
          name: "Mid 200–1000m",
          rules: [
            { id: "r2", field: "depth", operator: ">", value: "200" },
            { id: "r3", field: "depth", operator: "<=", value: "1000" },
          ],
          ts: 2,
        },
        {
          id: "f-deep",
          name: "Deep 1000m+",
          rules: [{ id: "r4", field: "depth", operator: ">", value: "1000" }],
          ts: 3,
        },
        {
          id: "f-temp",
          name: "Temp ≥ 15°C",
          rules: [{ id: "r5", field: "temp", operator: ">=", value: "15" }],
          ts: 4,
        },
      ],
      activeFilterId: "all",
      explorerSidebarCollapsed: false,

      createNewSession: () => {
        const newId = id();
        const newSession: ChatSession = {
          id: newId,
          title: "New Chat",
          messages: [],
          ts: Date.now(),
        };
        set((s) => ({
          sessions: [newSession, ...s.sessions],
          activeSessionId: newId,
          messages: [],
        }));
        return newId;
      },

      switchSession: (sessionId) => {
        set((s) => {
          const session = s.sessions.find((x) => x.id === sessionId);
          return {
            activeSessionId: sessionId,
            messages: session ? session.messages : [],
          };
        });
      },

      deleteSession: (sessionId) => {
        set((s) => {
          const nextSessions = s.sessions.filter((x) => x.id !== sessionId);
          let nextActiveId = s.activeSessionId;
          let nextMessages = s.messages;

          if (s.activeSessionId === sessionId) {
            if (nextSessions.length > 0) {
              nextActiveId = nextSessions[0].id;
              nextMessages = nextSessions[0].messages;
            } else {
              nextActiveId = null;
              nextMessages = [];
            }
          }
          return {
            sessions: nextSessions,
            activeSessionId: nextActiveId,
            messages: nextMessages,
          };
        });
      },

      addUser: (text) =>
        set((s) => {
          const newMessage: ChatMessage = { id: id(), role: "user", text, ts: Date.now() };
          let currentActiveId = s.activeSessionId;
          let nextSessions = [...s.sessions];

          if (!currentActiveId) {
            currentActiveId = id();
            const newSession: ChatSession = {
              id: currentActiveId,
              title: text.length > 25 ? text.slice(0, 25) + "..." : text,
              messages: [newMessage],
              ts: Date.now(),
            };
            nextSessions = [newSession, ...nextSessions];
            return {
              activeSessionId: currentActiveId,
              sessions: nextSessions,
              messages: [newMessage],
            };
          }

          nextSessions = nextSessions.map((session) => {
            if (session.id === currentActiveId) {
              const updatedMessages = [...session.messages, newMessage];
              const title =
                session.title === "New Chat" && session.messages.length === 0
                  ? text.length > 25
                    ? text.slice(0, 25) + "..."
                    : text
                  : session.title;
              return { ...session, messages: updatedMessages, title, ts: Date.now() };
            }
            return session;
          });

          const activeSession = nextSessions.find((x) => x.id === currentActiveId);

          return {
            sessions: nextSessions,
            messages: activeSession ? activeSession.messages : [],
          };
        }),

      addAi: (payload) =>
        set((s) => {
          const newMessage: ChatMessage = { id: id(), role: "ai", ts: Date.now(), payload };
          const currentActiveId = s.activeSessionId;
          if (!currentActiveId) return {};

          const nextSessions = s.sessions.map((session) => {
            if (session.id === currentActiveId) {
              return {
                ...session,
                messages: [...session.messages, newMessage],
                ts: Date.now(),
              };
            }
            return session;
          });

          const activeSession = nextSessions.find((x) => x.id === currentActiveId);

          return {
            sessions: nextSessions,
            messages: activeSession ? activeSession.messages : [],
          };
        }),

      setPending: (v) => set({ pending: v }),

      clear: () =>
        set((s) => {
          const currentActiveId = s.activeSessionId;
          if (!currentActiveId) return {};
          const nextSessions = s.sessions.map((session) => {
            if (session.id === currentActiveId) {
              return { ...session, messages: [] };
            }
            return session;
          });
          return {
            sessions: nextSessions,
            messages: [],
          };
        }),

      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      toggleChatSidebar: () => set((s) => ({ chatSidebarCollapsed: !s.chatSidebarCollapsed })),

      setSelectedOcean: (ocean) => set({ selectedOcean: ocean }),

      toggleTheme: () =>
        set((s) => {
          const next = s.theme === "dark" ? "light" : "dark";
          if (typeof document !== "undefined") {
            if (next === "light") {
              document.documentElement.classList.add("light");
              document.documentElement.classList.remove("dark");
            } else {
              document.documentElement.classList.add("dark");
              document.documentElement.classList.remove("light");
            }
          }
          return { theme: next };
        }),

      createExplorerFilter: (name, rules) => {
        const newId = "filter-" + id();
        const newFilter: ExplorerFilter = {
          id: newId,
          name,
          rules,
          ts: Date.now(),
        };
        set((s) => ({
          explorerFilters: [newFilter, ...s.explorerFilters],
          activeFilterId: newId,
        }));
        return newId;
      },

      updateExplorerFilter: (id, name, rules) => {
        set((s) => ({
          explorerFilters: s.explorerFilters.map((f) =>
            f.id === id ? { ...f, name, rules, ts: Date.now() } : f,
          ),
        }));
      },

      deleteExplorerFilter: (filterId) => {
        set((s) => {
          const nextFilters = s.explorerFilters.filter((x) => x.id !== filterId);
          let nextActiveId = s.activeFilterId;
          if (s.activeFilterId === filterId) {
            nextActiveId = "all";
          }
          return {
            explorerFilters: nextFilters,
            activeFilterId: nextActiveId,
          };
        });
      },

      setActiveFilterId: (filterId) => set({ activeFilterId: filterId }),
      toggleExplorerSidebar: () =>
        set((s) => ({ explorerSidebarCollapsed: !s.explorerSidebarCollapsed })),
    }),
    {
      name: "seaborg-chats-v1",
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        messages: state.messages,
        sidebarCollapsed: state.sidebarCollapsed,
        chatSidebarCollapsed: state.chatSidebarCollapsed,
        selectedOcean: state.selectedOcean,
        theme: state.theme,
        explorerFilters: state.explorerFilters,
        activeFilterId: state.activeFilterId,
        explorerSidebarCollapsed: state.explorerSidebarCollapsed,
      }),
    },
  ),
);
