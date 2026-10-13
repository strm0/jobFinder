export type ViewId = "top" | "lanes" | "phd" | "favourites" | "rejected" | "applied" | "dismissed";
export type Place = "all" | "stockholm" | "outside";
/** Where a list's jobs come from: every source, Platsbanken, or the other job sites JobAd Links
 *  lists. */
export type Source = "all" | "platsbanken" | "other";

/** A job site whose reader has stopped finding the ad text, so its new ads are held back. */
export interface ReaderFlag {
  site: string;
  tried: number;
  found: number;
  heldBack: number;
}

export interface Lane {
  code: string;
  id: string;
  name: string;
  short: string;
  count: number;
  newCount: number;
}

export interface Run {
  id: number;
  startedUtc: string;
  added: number;
  removed: number;
  open: number;
}

export interface Overview {
  classifierVersion: string;
  warning: string | null;
  lanes: Lane[];
  counts: { top: number; phd: number; favourites: number; rejected: number; applied: number; dismissed: number };
  newCounts: { top: number; phd: number; rejected: number };
  run: Run | null;
  place: Place;
  source: Source;
  /** Job sites whose reader needs fixing. Empty when every reader is finding text. */
  readers: ReaderFlag[];
  /** Every starred job, whatever the place, unlike `counts.favourites`. A removed job is not counted. */
  starredTotal: number;
  /** Every applied job, whatever the place, unlike `counts.applied`. */
  appliedTotal: number;
  /** Every job in Removed, whatever the place, unlike `counts.dismissed`. */
  dismissedTotal: number;
}

export interface JobLane {
  code: string;
  name: string;
  short: string;
  fit: number | null;
}

export interface Job {
  id: string;
  rank: number | null;
  title: string;
  employer: string | null;
  city: string | null;
  otherCities: string[];
  lanes: JobLane[];
  summary: string | null;
  score: number | null;
  want: number | null;
  reach: number | null;
  wantWhy: string | null;
  reachWhy: string | null;
  applyBy: string | null;
  employmentType: string | null;
  url: string;
  /** "links" for an ad from another job site, with that site in `site`. */
  source: "platsbanken" | "links";
  site: string | null;
  isNew: boolean;
  starred: boolean;
  closed: boolean;
  hasApplication: boolean;
  applied: boolean;
  /** When the job was marked applied, as the server's UTC timestamp; null unless applied. */
  appliedAt: string | null;
  /** Removed with the x on its card, and waiting in Removed until the next run. */
  dismissed: boolean;
}

export interface JobPage {
  view: ViewId;
  total: number;
  page: number;
  pages: number;
  pageSize: number;
  jobs: Job[];
  place: Place;
  onlyNew: boolean;
  source: Source;
}

export interface BriefResult {
  status: "created" | "exists";
  path: string;
  command: string;
}

export type BriefState =
  | { state: "working" }
  | { state: "created" | "exists"; path: string; command: string }
  | { state: "error"; message: string };
