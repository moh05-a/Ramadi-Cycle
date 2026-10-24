import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./guide/App";
import "./guide/guide.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
