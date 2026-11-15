export function AppIcon({ name, size = 18 }: { name: "today" | "workflows" | "history" | "browser" | "about" | "ai" | "check" | "arrow"; size?: number }) {
  const paths = {
    today: "M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
    workflows: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    history: "M4 6h16v15H4zM4 10h16M8 3v5m8-5v5M8 14h2m4 0h2m-8 3h2",
    browser: "M3 4h18v16H3zM3 9h18M7 6.5h.1m3 0h.1M8 14l-2 2 2 2m8-4 2 2-2 2",
    about: "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a8 8 0 0 1 16 0v2",
    ai: "M3 12h4l3-7 4 14 3-7h4",
    check: "m5 12 4 4L19 6",
    arrow: "M4 12h16m-6-6 6 6-6 6",
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
