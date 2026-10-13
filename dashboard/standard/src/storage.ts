// What the page remembers between visits in this browser: the view, the lane, the place and the
// theme. Remembering is a convenience, so every call works when storage is blocked.

export function readSaved(key: string, fallback: string): string {
  try {
    return localStorage.getItem(`standard.${key}`) ?? fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: string) {
  try {
    localStorage.setItem(`standard.${key}`, value);
  } catch {
    // The page works without it.
  }
}

export function forget(key: string) {
  try {
    localStorage.removeItem(`standard.${key}`);
  } catch {
    // The page works without it.
  }
}
