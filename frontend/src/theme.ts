// Light/dark follows the system until the user picks one. The choice is remembered when storage allows it.
import { useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "rc.theme";

function initial(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch { /* storage blocked: follow the system */ }
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initial);
  useEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try { localStorage.setItem(KEY, next); } catch { /* keep in memory */ }
  };
  return { theme, toggle };
}
