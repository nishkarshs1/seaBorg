import { useEffect } from "react";
import { Link, useRouterState, Outlet } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard,
  MessageSquareText,
  Globe2,
  BarChart3,
  Workflow,
  ChevronLeft,
  Waves,
  ShieldCheck,
  Sun,
  Moon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useStore } from "@/store";
import { getHealth } from "@/lib/api";
import { StatusDot } from "@/components/ui/StatusDot";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/chat", label: "Ocean Chat", icon: MessageSquareText },
  { to: "/explorer", label: "Data Explorer", icon: Globe2 },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/evaluation", label: "System Reliability", icon: ShieldCheck },
  { to: "/about", label: "Architecture", icon: Workflow },
] as const;

export function SidebarLayout() {
  const collapsed = useStore((s) => s.sidebarCollapsed);
  const toggle = useStore((s) => s.toggleSidebar);
  const pathname = useRouterState({ select: (r) => r.location.pathname });

  const theme = useStore((s) => s.theme);
  const toggleTheme = useStore((s) => s.toggleTheme);

  useEffect(() => {
    if (typeof document !== "undefined") {
      if (theme === "light") {
        document.documentElement.classList.add("light");
        document.documentElement.classList.remove("dark");
      } else {
        document.documentElement.classList.add("dark");
        document.documentElement.classList.remove("light");
      }
    }
  }, [theme]);

  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      return data?.status === "ok" ? 30_000 : 3_000;
    },
    staleTime: 0,
  });
  const online = health.data?.status === "ok";

  return (
    <div className="flex min-h-screen w-full">
      <aside
        className={cn(
          "sticky top-0 z-30 flex h-screen shrink-0 flex-col border-r border-[var(--glass-border)] bg-card transition-[width] duration-300",
          collapsed ? "w-[68px]" : "w-[244px]",
        )}
      >
        <div className="flex items-center gap-2 px-4 py-5">
          <div
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg"
            style={{
              background: "linear-gradient(135deg, rgba(0,212,170,0.18), rgba(0,168,255,0.18))",
              border: "1px solid rgba(0,212,170,0.35)",
            }}
          >
            <Waves className="h-4 w-4 text-teal" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="font-semibold leading-none tracking-tight">SeaBorg</div>
              <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Ocean Intelligence
              </div>
            </div>
          )}
        </div>

        <nav className="flex-1 px-3 py-2">
          <ul className="flex flex-col gap-1">
            {navItems.map((item) => {
              const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                      active
                        ? "text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]",
                    )}
                    style={
                      active
                        ? {
                            background:
                              "linear-gradient(90deg, rgba(0,212,170,0.12), rgba(0,212,170,0.02))",
                            boxShadow: "inset 3px 0 0 0 #00d4aa",
                          }
                        : undefined
                    }
                  >
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0",
                        active ? "text-teal" : "text-muted-foreground group-hover:text-foreground",
                      )}
                    />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-[var(--glass-border)] p-3">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={cn(
              "mb-2 flex w-full items-center gap-2.5 rounded-lg border border-[var(--glass-border)] bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground transition-all hover:bg-white/[0.05] hover:text-foreground",
              collapsed ? "justify-center" : "",
            )}
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? (
              <>
                <Sun className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                {!collapsed && <span className="font-medium">Light Mode</span>}
              </>
            ) : (
              <>
                <Moon className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                {!collapsed && <span className="font-medium">Dark Mode</span>}
              </>
            )}
          </button>

          <div
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2",
              collapsed ? "justify-center" : "",
            )}
            style={{ background: online ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)" }}
          >
            <StatusDot color={online ? "green" : "red"} />
            {!collapsed && (
              <div className="min-w-0 leading-tight">
                <div className="text-[11px] font-medium text-foreground">
                  System {online ? "Online" : "Offline"}
                </div>
                <div className="font-mono text-[10px] text-muted-foreground">seaborg-api</div>
              </div>
            )}
          </div>
          <button
            onClick={toggle}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--glass-border)] bg-white/[0.02] px-2 py-2 text-xs text-muted-foreground transition-colors hover:bg-white/[0.05] hover:text-foreground"
            aria-label="Toggle sidebar"
          >
            <ChevronLeft
              className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")}
            />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <AnimatePresence mode="wait">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="flex-1"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
