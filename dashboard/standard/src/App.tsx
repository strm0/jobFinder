import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { Inbox, SearchX, Send, Star, Trash2 } from "lucide-react";
import { api } from "./api";
import { message } from "./format";
import type { BriefState, Job, JobPage, Overview, Place, ReaderFlag, Source, ViewId } from "./types";
import { Header } from "./components/Header";
import { JobCard } from "./components/JobCard";
import { JobPanel } from "./components/JobPanel";
import { LanePicker } from "./components/LanePicker";
import { MoreJobs, type More } from "./components/MoreJobs";
import { EmptyState, Notice, SkeletonGrid } from "./components/States";
import { Toolbar } from "./components/Toolbar";
import { readSaved, save } from "./storage";

interface Filters {
  view: ViewId;
  lane: string;
  place: Place;
  source: Source;
  onlyNew: boolean;
}

const VIEWS: readonly string[] = ["top", "lanes", "phd", "favourites", "rejected", "applied", "dismissed"];
const PLACES: readonly string[] = ["all", "stockholm", "outside"];
const SOURCES: readonly string[] = ["all", "platsbanken", "other"];

// The place and the source are remembered between visits. New is not, since it is a question
// asked afresh on each visit.
function initialFilters(): Filters {
  const view = readSaved("view", "top");
  const place = readSaved("place", "all");
  const source = readSaved("source", "all");
  return {
    view: (VIEWS.includes(view) ? view : "top") as ViewId,
    lane: readSaved("lane", "L1"),
    place: (PLACES.includes(place) ? place : "all") as Place,
    source: (SOURCES.includes(source) ? source : "all") as Source,
    onlyNew: false,
  };
}

/** "thehub.io found the ad text on 0 of 12 pages", one sentence per flagged site. */
function readerText(flags: ReaderFlag[]): string {
  const sites = flags.map(
    (f) =>
      `${f.site} found the ad text on ${f.found} of ${f.tried} pages in its last read, and holds back ${f.heldBack} ${f.heldBack === 1 ? "ad" : "ads"}`,
  );
  return `${sites.join("; ")}. Those ads are not shown until the reader is fixed in pipeline/links.py. Run python -m pipeline.links status for more.`;
}

/** Cards glide to their new places and the panel slides in beside them. Instant when the
 *  reader asks for reduced motion or the browser has no view transitions. */
function transition(update: () => void) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || typeof document.startViewTransition !== "function") {
    update();
    return;
  }
  // Only the cards within a screen of view glide. A long scrolled list would otherwise have the
  // browser capture every card first, which delays the start of the glide by a visible pause.
  const far = [...document.querySelectorAll<HTMLElement>(".grid .card")].filter((card) => {
    const box = card.getBoundingClientRect();
    return box.bottom < -window.innerHeight || box.top > 2 * window.innerHeight;
  });
  far.forEach((card) => card.setAttribute("data-far", ""));
  document
    .startViewTransition(() => flushSync(update))
    .finished.catch(() => undefined)
    .finally(() => far.forEach((card) => card.removeAttribute("data-far")));
}

function newCountFor(filters: Filters, overview: Overview | null): number | null {
  if (!overview) return null;
  if (filters.view === "top") return overview.newCounts.top;
  if (filters.view === "phd") return overview.newCounts.phd;
  if (filters.view === "rejected") return overview.newCounts.rejected;
  if (filters.view === "lanes") return overview.lanes.find((l) => l.code === filters.lane)?.newCount ?? null;
  return null;
}

function listHeading(filters: Filters, overview: Overview | null): string {
  switch (filters.view) {
    case "lanes": {
      const lane = overview?.lanes.find((l) => l.code === filters.lane);
      return lane ? `${lane.code} ${lane.name}` : "By lane";
    }
    case "phd":
      return "PhD";
    case "favourites":
      return "Saved";
    case "rejected":
      return "Rejected";
    case "applied":
      return "Applied";
    case "dismissed":
      return "Removed";
    default:
      return "Top picks";
  }
}

export function App() {
  const [baseline, setBaseline] = useState<string | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [list, setList] = useState<JobPage | null>(null);
  const [busy, setBusy] = useState(false);
  const [more, setMore] = useState<More>({ state: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [briefs, setBriefs] = useState<Record<string, BriefState>>({});
  const headerRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const latest = useRef(0);
  const fetchingMore = useRef(false);
  // The card to focus once a removal has taken the focused one off the list, or "" for the list.
  const focusAfter = useRef<string | null>(null);

  const refreshOverview = useCallback(async (base: string | null, place: Place, source: Source) => {
    try {
      setOverview(await api.overview(base, place, source));
    } catch (e) {
      setError(message(e));
    }
  }, []);

  // The first ten of a list. Anything still arriving for the list before it is dropped.
  const load = useCallback(async (next: Filters, base: string | null) => {
    save("view", next.view);
    save("lane", next.lane);
    save("place", next.place);
    save("source", next.source);
    const request = ++latest.current;
    fetchingMore.current = false;
    setMore({ state: "idle" });
    setBusy(true);
    try {
      const data = await api.jobs(next.view, next.lane, 1, base, next.place, next.onlyNew, next.source);
      if (request !== latest.current) return;
      transition(() => {
        setList(data);
        setError(null);
        setBusy(false);
      });
    } catch (e) {
      if (request === latest.current) {
        setError(message(e));
        setBusy(false);
      }
    }
  }, []);

  // The next ten, when the user asks for them. They join the list below the others without the
  // glide, which belongs to changing the list, and focus moves to the first of them, so a keyboard
  // carries on from there without the page moving.
  const loadMore = async () => {
    if (!list || busy || fetchingMore.current || list.jobs.length >= list.total) return;
    const request = latest.current;
    fetchingMore.current = true;
    setMore({ state: "loading" });
    try {
      // From the number on screen rather than the next page, so a job removed from the list does not
      // push another past the fetch unseen.
      const data = await api.jobs(
        list.view,
        filters.lane,
        list.page + 1,
        baseline,
        list.place,
        list.onlyNew,
        list.source,
        list.jobs.length,
      );
      if (request !== latest.current) return;
      // A nightly run between two fetches can move a job down a place, so none is shown twice.
      const shown = new Set(list.jobs.map((j) => j.id));
      const added = data.jobs.filter((j) => !shown.has(j.id));
      flushSync(() => {
        setList((cur) => cur && { ...data, jobs: [...cur.jobs, ...added] });
        setMore({ state: "idle" });
      });
      if (added[0]) {
        document.querySelector<HTMLButtonElement>(`#card-${CSS.escape(added[0].id)} .card-open`)?.focus({ preventScroll: true });
      }
    } catch (e) {
      if (request === latest.current) setMore({ state: "error", message: message(e) });
    } finally {
      if (request === latest.current) fetchingMore.current = false;
    }
  };

  // First the visit, which fixes what counts as new for this sitting; then the list.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { baseline: base } = await api.visit();
        if (cancelled) return;
        setBaseline(base);
        const first = await api.overview(base, filters.place, filters.source);
        if (cancelled) return;
        setOverview(first);
        const known = first.lanes.some((l) => l.code === filters.lane);
        const next = { ...filters, lane: known ? filters.lane : (first.lanes[0]?.code ?? filters.lane) };
        setFilters(next);
        await load(next, base);
      } catch (e) {
        if (!cancelled) setError(message(e));
      }
    })();
    return () => {
      cancelled = true;
    };
    // Runs once on load; later changes go through `change`.
  }, []);

  // The panel sticks below the header, whose height changes with the lane row.
  useEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const observer = new ResizeObserver(() => {
      document.documentElement.style.setProperty("--header-h", `${header.offsetHeight}px`);
    });
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  // Opening a job moves focus to its title and keeps its card in view as the grid narrows.
  useEffect(() => {
    if (!selected) return;
    titleRef.current?.focus({ preventScroll: true });
    document.getElementById(`card-${selected.id}`)?.scrollIntoView({ block: "nearest" });
  }, [selected?.id]);

  // A removed card takes focus with it, so focus moves to the card that took its place, or to the
  // list when none is left.
  useEffect(() => {
    const next = focusAfter.current;
    if (next === null) return;
    focusAfter.current = null;
    const card = next ? document.querySelector<HTMLButtonElement>(`#card-${CSS.escape(next)} .card-open`) : null;
    (card ?? document.getElementById("jobs"))?.focus({ preventScroll: true });
  }, [list]);

  const change = (patch: Partial<Filters>) => {
    const next: Filters = { ...filters, ...patch };
    setFilters(next);
    // A different list starts at its top, however far down the last one was scrolled.
    window.scrollTo({ top: 0 });
    if (next.place !== filters.place || next.source !== filters.source) {
      void refreshOverview(baseline, next.place, next.source);
    }
    void load(next, baseline);
  };

  const openJob = (job: Job) => {
    if (selected?.id === job.id) {
      closePanel();
      return;
    }
    transition(() => setSelected(job));
  };

  const closePanel = () => {
    const id = selected?.id;
    transition(() => setSelected(null));
    if (id) {
      requestAnimationFrame(() => {
        document.querySelector<HTMLButtonElement>(`#card-${CSS.escape(id)} .card-open`)?.focus({ preventScroll: true });
      });
    }
  };

  // Escape closes the panel, unless focus is in a text field.
  useEffect(() => {
    if (!selected) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const el = event.target as HTMLElement | null;
      if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      event.preventDefault();
      closePanel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const patchJob = (id: string, update: Partial<Job>) => {
    setList((cur) => cur && { ...cur, jobs: cur.jobs.map((j) => (j.id === id ? { ...j, ...update } : j)) });
    setSelected((cur) => (cur && cur.id === id ? { ...cur, ...update } : cur));
  };

  const toggleStar = async (job: Job) => {
    const starred = !job.starred;
    patchJob(job.id, { starred });
    try {
      await api.star(job.id, starred);
      void refreshOverview(baseline, filters.place, filters.source);
    } catch (e) {
      patchJob(job.id, { starred: !starred });
      setError(message(e));
    }
  };

  // Applied and saved are one status on the server, so marking a saved job applied unsaves it, and
  // undoing leaves it unsaved. The card stays where it is until the list loads again, so a
  // misclick can be undone in place.
  const toggleApplied = async (job: Job) => {
    const applied = !job.applied;
    const before = { applied: job.applied, appliedAt: job.appliedAt, starred: job.starred };
    patchJob(job.id, { applied, appliedAt: applied ? new Date().toISOString() : null, starred: false });
    try {
      const result = await api.applied(job.id, applied);
      patchJob(job.id, { appliedAt: result.appliedAt });
      void refreshOverview(baseline, filters.place, filters.source);
    } catch (e) {
      patchJob(job.id, before);
      setError(message(e));
    }
  };

  // The x takes a job off the list into Removed, and Restore takes it back out. Either way the card
  // fades from the list it is in and the cards after it close the gap. A job stays in Removed until
  // the next run starts, and then it shows nowhere.
  const setDismissed = async (job: Job, dismissed: boolean) => {
    const jobs = list?.jobs ?? [];
    const index = jobs.findIndex((j) => j.id === job.id);
    if (index < 0) return;
    const request = latest.current;
    focusAfter.current = (jobs[index + 1] ?? jobs[index - 1])?.id ?? "";
    setOverview(
      (cur) =>
        cur && {
          ...cur,
          dismissedTotal: cur.dismissedTotal + (dismissed ? 1 : -1),
          starredTotal: cur.starredTotal + (job.starred ? (dismissed ? -1 : 1) : 0),
        },
    );
    transition(() => {
      setList((cur) => cur && { ...cur, total: cur.total - 1, jobs: cur.jobs.filter((j) => j.id !== job.id) });
      setSelected((cur) => (cur?.id === job.id ? null : cur));
    });
    try {
      await api.dismiss(job.id, dismissed);
    } catch (e) {
      // The card goes back where it was, unless another list has loaded since.
      if (request === latest.current) {
        transition(() =>
          setList((cur) => {
            if (!cur) return cur;
            const back = [...cur.jobs];
            back.splice(Math.min(index, back.length), 0, job);
            return { ...cur, total: cur.total + 1, jobs: back };
          }),
        );
      }
      setError(message(e));
    }
    void refreshOverview(baseline, filters.place, filters.source);
  };

  // One brief serves both /cv and /letter, so there is one action to write it.
  const writeBrief = async (job: Job) => {
    setBriefs((b) => ({ ...b, [job.id]: { state: "working" } }));
    try {
      const result = await api.brief(job.id);
      setBriefs((b) => ({
        ...b,
        [job.id]: { state: result.status, path: result.path, command: result.command },
      }));
      patchJob(job.id, { hasApplication: true });
    } catch (e) {
      setBriefs((b) => ({ ...b, [job.id]: { state: "error", message: message(e) } }));
    }
  };

  const empty = () => {
    if (filters.view === "favourites" && (overview?.starredTotal ?? 0) === 0) {
      return (
        <EmptyState icon={<Star size={24} />} title="Nothing saved yet">
          Save a job with its star in any list and it is kept here, best match first.
        </EmptyState>
      );
    }
    if (filters.view === "applied" && (overview?.appliedTotal ?? 0) === 0) {
      return (
        <EmptyState icon={<Send size={24} />} title="Nothing applied yet">
          Open a job and press Mark applied at the bottom of its details. It moves here, most recent first.
        </EmptyState>
      );
    }
    if (filters.view === "dismissed" && (overview?.dismissedTotal ?? 0) === 0) {
      return (
        <EmptyState icon={<Trash2 size={24} />} title="Nothing removed">
          Remove a job with the x on its card. It waits here until the next daily run, and then it is gone for good.
        </EmptyState>
      );
    }
    if (filters.onlyNew) {
      const where = filters.place === "stockholm" ? " in Stockholm" : filters.place === "outside" ? " outside Stockholm" : "";
      return (
        <EmptyState
          icon={<Inbox size={24} />}
          title={`Nothing new${where} since you last looked`}
          action={
            <button type="button" className="btn" onClick={() => change({ onlyNew: false })}>
              Show all jobs
            </button>
          }
        >
          New shows the jobs from every nightly run since your previous visit. A run starts the first time each day the computer is on power.
        </EmptyState>
      );
    }
    if (filters.place === "all" && filters.source !== "all") {
      return (
        <EmptyState
          icon={<SearchX size={24} />}
          title={filters.source === "other" ? "Nothing here from other sites" : "Nothing here from Platsbanken"}
          action={
            <button type="button" className="btn" onClick={() => change({ source: "all" })}>
              Show all sites
            </button>
          }
        >
          This list has no open jobs from there right now.
        </EmptyState>
      );
    }
    if (filters.place !== "all") {
      return (
        <EmptyState
          icon={<SearchX size={24} />}
          title={filters.place === "stockholm" ? "Nothing here in Stockholm" : "Nothing here outside Stockholm"}
          action={
            <button type="button" className="btn" onClick={() => change({ place: "all" })}>
              Show everywhere
            </button>
          }
        >
          This list has no open jobs in that area right now.
        </EmptyState>
      );
    }
    if (filters.view === "rejected") {
      return (
        <EmptyState icon={<SearchX size={24} />} title="Nothing rejected right now">
          Every open job the model read went into a lane or was stopped by a hard filter.
        </EmptyState>
      );
    }
    return (
      <EmptyState icon={<SearchX size={24} />} title={filters.view === "phd" ? "No open doctoral calls" : "No open jobs here"}>
        Nothing in this list is open and eligible right now.
      </EmptyState>
    );
  };

  return (
    <>
      <a className="skip" href="#jobs">
        Skip to the jobs
      </a>
      <Header
        headerRef={headerRef}
        overview={overview}
        count={
          list ? { view: list.view, total: list.total, onlyNew: list.onlyNew, place: list.place, source: list.source } : null
        }
      >
        <Toolbar
          view={filters.view}
          favourites={overview?.starredTotal ?? 0}
          applied={overview?.appliedTotal ?? 0}
          dismissed={overview?.dismissedTotal ?? 0}
          place={filters.place}
          source={filters.source}
          onlyNew={filters.onlyNew}
          newCount={newCountFor(filters, overview)}
          onView={(view) => {
            if (selected) setSelected(null);
            change({ view });
          }}
          onPlace={(place) => change({ place })}
          onSource={(source) => change({ source })}
          onNew={(onlyNew) => change({ onlyNew })}
        />
        {filters.view === "lanes" && overview && (
          <LanePicker
            lanes={overview.lanes}
            selected={filters.lane}
            onSelect={(lane) => {
              if (lane !== filters.lane) change({ lane });
            }}
          />
        )}
      </Header>

      <main className="shell main" id="jobs" tabIndex={-1}>
        {overview?.warning && <Notice title="The ranking may be stale">{overview.warning}</Notice>}
        {/* A job site's reader that stops finding text holds its new ads back without failing, so it
            is named here to be fixed. */}
        {overview && overview.readers.length > 0 && (
          <Notice title={overview.readers.length === 1 ? "A job site's reader needs fixing" : "Job site readers need fixing"}>
            {readerText(overview.readers)}
          </Notice>
        )}
        {error && (
          <Notice
            tone="error"
            title="Something went wrong"
            action={
              <button type="button" className="btn btn-small" onClick={() => window.location.reload()}>
                Reload
              </button>
            }
          >
            {error}
          </Notice>
        )}

        {list === null ? (
          <SkeletonGrid />
        ) : (
          <div className="workspace" data-open={selected ? "" : undefined}>
            <section className="results" aria-labelledby="results-title" aria-busy={busy}>
              <h2 className="sr-only" id="results-title">
                {listHeading(filters, overview)}
              </h2>
              {list.total === 0 ? (
                empty()
              ) : (
                <>
                  {list.view === "dismissed" && (
                    <p className="list-note">
                      Removed jobs wait here until the next daily run, and then they are gone for good. Restore puts a
                      job back where it was.
                    </p>
                  )}
                  <ol className="grid">
                    {list.jobs.map((job) => (
                      <li key={job.id}>
                        <JobCard
                          job={job}
                          selected={selected?.id === job.id}
                          onOpen={() => openJob(job)}
                          onStar={() => void toggleStar(job)}
                          onRemove={() => void setDismissed(job, true)}
                          onRestore={() => void setDismissed(job, false)}
                        />
                      </li>
                    ))}
                  </ol>
                  {list.total > list.pageSize && (
                    <MoreJobs
                      shown={list.jobs.length}
                      total={list.total}
                      pageSize={list.pageSize}
                      hasMore={list.jobs.length < list.total}
                      more={more}
                      onMore={() => void loadMore()}
                    />
                  )}
                </>
              )}
            </section>
            {selected && (
              <JobPanel
                job={selected}
                brief={briefs[selected.id]}
                titleRef={titleRef}
                onClose={closePanel}
                onStar={() => void toggleStar(selected)}
                onBrief={() => void writeBrief(selected)}
                onApplied={() => void toggleApplied(selected)}
                onRestore={() => void setDismissed(selected, false)}
              />
            )}
          </div>
        )}
      </main>
    </>
  );
}
