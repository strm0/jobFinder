const numbers = new Intl.NumberFormat("en-GB");

export const fmt = (n: number): string => numbers.format(n);

export function formatDate(isoDate: string): string {
  const day = new Date(`${isoDate.slice(0, 10)}T00:00:00`);
  return day.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** The day a server timestamp falls on here, rather than in UTC, where a mark made after
 *  midnight would still read as the day before. */
export function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatRunTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

// JobTech's employment types, a small fixed set, in the interface's English. A type that is not
// listed here shows as JobTech wrote it.
const EMPLOYMENT: Record<string, string> = {
  "Vanlig anställning": "Regular employment",
  "Tillsvidareanställning": "Permanent employment",
  "Behovsanställning": "On-call employment",
  "Tidsbegränsad anställning": "Fixed-term employment",
  "Vikariat": "Temporary cover",
  "Säsongsanställning": "Seasonal employment",
  "Sommarjobb / feriejobb": "Summer job",
};

export function employmentLabel(kind: string): string {
  return EMPLOYMENT[kind] ?? kind;
}

/** "Stockholm", "Stockholm and 2 more", or "Place not given" when the ad names none. */
export function placeShort(city: string | null, others: string[]): string {
  const all = [city, ...others].filter((c): c is string => Boolean(c));
  if (all.length === 0) return "Place not given";
  return all.length === 1 ? all[0] : `${all[0]} and ${all.length - 1} more`;
}

/** Every city a card stands for, the folded reposts included. */
export function placeFull(city: string | null, others: string[]): string {
  const all = [city, ...others].filter((c): c is string => Boolean(c));
  if (all.length === 0) return "Place not given";
  if (all.length === 1) return all[0];
  return `${all.slice(0, -1).join(", ")} and ${all[all.length - 1]}`;
}
