import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { forget, readSaved, save } from "../storage";

type Theme = "light" | "dark";

const SYSTEM_DARK = "(prefers-color-scheme: dark)";

function systemTheme(): Theme {
  return window.matchMedia(SYSTEM_DARK).matches ? "dark" : "light";
}

function savedTheme(): Theme | null {
  const saved = readSaved("theme", "");
  return saved === "light" || saved === "dark" ? saved : null;
}

/** Every colour changes in the same frame, rather than each control fading over at its own speed.
 *  Reading the layout makes the browser take the new colours while transitions are off. */
function apply(theme: Theme) {
  const root = document.documentElement;
  root.setAttribute("data-theme-switching", "");
  root.dataset.theme = theme;
  void root.offsetWidth;
  requestAnimationFrame(() => root.removeAttribute("data-theme-switching"));
}

/** Flips the page between light and dark. With no choice saved the page follows the computer.
 *  index.html sets the theme the same way before the page draws, so this only has to keep up with
 *  changes. */
export function ThemeButton() {
  const [theme, setTheme] = useState<Theme>(() => savedTheme() ?? systemTheme());

  // Following the computer includes when it changes while the page is open, as it can at dusk.
  useEffect(() => {
    const query = window.matchMedia(SYSTEM_DARK);
    const follow = () => {
      if (savedTheme()) return;
      const next = systemTheme();
      apply(next);
      setTheme(next);
    };
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, []);

  const flip = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    // Flipping back to what the computer shows is no choice at all, so the page follows it again.
    if (next === systemTheme()) forget("theme");
    else save("theme", next);
    apply(next);
    setTheme(next);
  };

  const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
  return (
    <button type="button" className="icon-btn theme-button" aria-label={label} title={label} onClick={flip}>
      {theme === "dark" ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}
    </button>
  );
}
