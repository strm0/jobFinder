import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Newsreader is installed locally, so the page makes no outside request for type. fonts.css loads
// the optical size axis with the weights, so small text is drawn sturdier and headlines finer, and
// corrects the font's vertical metrics so text sits centred in buttons and chips.
import "./fonts.css";
import "./styles.css";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
