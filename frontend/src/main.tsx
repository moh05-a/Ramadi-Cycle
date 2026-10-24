import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Fonts are bundled so the app makes no network calls at runtime.
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import { App } from "./App";
import "./app.css";
import "./shell.css";
import "./garden.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
