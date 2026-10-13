import type { BriefResult, JobPage, Overview, Place, Source, ViewId } from "./types";

// This design reads the second half of the API, which adds the location switch and New, and
// counts a job new from when it was classified. See dashboard/serve.py.
const BASE = "/api/v2";

const OFFLINE =
  "The dashboard server is not answering. Start it with python -m dashboard.serve --ui standard and reload.";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    // The custom header is how the server tells its own page from any other site.
    response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", "X-Dashboard": "1" },
    });
  } catch {
    throw new Error(OFFLINE);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const said =
      body !== null && typeof body === "object" && "error" in body
        ? String((body as { error: unknown }).error)
        : `The server answered ${response.status}.`;
    throw new Error(said);
  }
  return body as T;
}

function query(params: Record<string, string | number | null>): string {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null) q.set(key, String(value));
  }
  return q.toString();
}

export const api = {
  visit: () => request<{ baseline: string | null }>(`${BASE}/visit`, { method: "POST", body: "{}" }),
  overview: (baseline: string | null, place: Place, source: Source) =>
    request<Overview>(`${BASE}/overview?${query({ baseline, place, source })}`),
  /** With an offset the page starts at that job, not at the start of `page`. */
  jobs: (
    view: ViewId,
    lane: string,
    page: number,
    baseline: string | null,
    place: Place,
    onlyNew: boolean,
    source: Source,
    offset: number | null = null,
  ) =>
    request<JobPage>(
      `${BASE}/jobs?${query({ view, lane, page, baseline, place, new: onlyNew ? 1 : 0, source, offset })}`,
    ),
  star: (id: string, starred: boolean) =>
    request<{ id: string; starred: boolean }>(`${BASE}/star`, {
      method: "POST",
      body: JSON.stringify({ id, starred }),
    }),
  applied: (id: string, applied: boolean) =>
    request<{ id: string; applied: boolean; appliedAt: string | null }>(`${BASE}/applied`, {
      method: "POST",
      body: JSON.stringify({ id, applied }),
    }),
  dismiss: (id: string, dismissed: boolean) =>
    request<{ id: string; dismissed: boolean }>(`${BASE}/dismiss`, {
      method: "POST",
      body: JSON.stringify({ id, dismissed }),
    }),
  brief: (id: string) =>
    request<BriefResult>(`${BASE}/brief`, { method: "POST", body: JSON.stringify({ id }) }),
};
