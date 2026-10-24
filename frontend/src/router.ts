// Hash routing: works from a file or any static host, and needs no server rewrite rules.
import { useEffect, useState } from "react";

export const ROUTES = ["", "home", "dashboard", "plan", "method", "data", "save", "calc", "garden"] as const;
export type Route = (typeof ROUTES)[number];

function parse(hash: string): Route {
  const r = hash.replace(/^#\/?/, "").split(/[/?]/)[0];
  return (ROUTES as readonly string[]).includes(r) ? (r as Route) : "";
}

export const href = (r: Route) => `#/${r}`;

export function useRoute() {
  const [route, setRoute] = useState<Route>(() => parse(location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parse(location.hash));
      window.scrollTo(0, 0);
      // move focus to the new page's heading so screen readers announce it
      requestAnimationFrame(() => document.querySelector<HTMLElement>("main h1")?.focus());
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
