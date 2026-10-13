import type { ReactNode, Ref } from "react";
import { fmt, formatRunTime } from "../format";
import type { Overview, Place, Run, Source, ViewId } from "../types";
import { Logo } from "./Logo";
import { ThemeButton } from "./ThemeButton";

/** What the list below is showing, for the count at the end of the run line. */
export interface ListCount {
  view: ViewId;
  total: number;
  onlyNew: boolean;
  place: Place;
  source: Source;
}

interface HeaderProps {
  headerRef: Ref<HTMLElement>;
  overview: Overview | null;
  /** Null while the first list loads. */
  count: ListCount | null;
  children?: ReactNode;
}

export function Header({ headerRef, overview, count, children }: HeaderProps) {
  return (
    <header className="header" ref={headerRef}>
      <div className="shell header-top">
        <h1 className="wordmark">
          <Logo />
          jobFinder
        </h1>
        <ThemeButton />
        <RunLine run={overview ? overview.run : undefined} count={count} />
      </div>
      {children}
    </header>
  );
}

/** `run` is undefined while loading and null when no nightly run has been recorded. The first
 *  number names what it counts, job listings, so the night's intake is not read as new jobs for
 *  the user; the noun carries through the rest of the line. */
function RunLine({ run, count }: { run: Run | null | undefined; count: ListCount | null }) {
  if (run === undefined) {
    return (
      <p className="run" aria-hidden="true">
        &nbsp;
      </p>
    );
  }
  return (
    <p className="run">
      {run === null ? (
        <span>No nightly run recorded yet</span>
      ) : (
        <>
          <span>Last run {formatRunTime(run.startedUtc)}</span>
          <Separator />
          <span>
            <strong>{fmt(run.added)}</strong> {run.added === 1 ? "job listing" : "job listings"} added
          </span>
          <Separator />
          <span>
            <strong>{fmt(run.removed)}</strong> removed
          </span>
          <Separator />
          <span>
            <strong>{fmt(run.open)}</strong> open
          </span>
        </>
      )}
      <span className="run-match" aria-live="polite">
        {count && (
          <>
            <Separator />
            <span>
              <MatchText {...count} />
            </span>
          </>
        )}
      </span>
    </p>
  );
}

function Separator() {
  return (
    <span className="run-sep" aria-hidden="true">
      ·
    </span>
  );
}

/** "44 jobs match your profile", worded for the view and the filters. Saved, applied and
 *  removed jobs are the user's own rather than matches, so they only say how many, and Rejected
 *  holds the jobs the model put in no lane, so it says that. */
function MatchText({ view, total, onlyNew, place, source }: ListCount) {
  const one = total === 1;
  const noun =
    view === "phd"
      ? one ? "doctoral call" : "doctoral calls"
      : view === "favourites"
        ? one ? "saved job" : "saved jobs"
        : view === "applied"
          ? one ? "applied job" : "applied jobs"
          : view === "dismissed"
            ? one ? "removed job" : "removed jobs"
            : one ? "job" : "jobs";
  const where = place === "stockholm" ? " in Stockholm" : place === "outside" ? " outside Stockholm" : "";
  const from = source === "platsbanken" ? " from Platsbanken" : source === "other" ? " from other sites" : "";
  const verb =
    view === "favourites" || view === "applied" || view === "dismissed"
      ? ""
      : view === "rejected" ? " matched no lane" : one ? " matches your profile" : " match your profile";
  return (
    <>
      <strong>{fmt(total)}</strong>
      {onlyNew ? " new " : " "}
      {noun}
      {where}
      {from}
      {verb}
    </>
  );
}
