import { fmt } from "../format";

/** What fetching more of the list is doing: waiting, fetching, or stopped by an error. */
export type More = { state: "idle" } | { state: "loading" } | { state: "error"; message: string };

interface MoreJobsProps {
  shown: number;
  total: number;
  pageSize: number;
  hasMore: boolean;
  more: More;
  onMore: () => void;
}

/** The end of the list. A list opens with ten jobs, and the button adds the next ten below them,
 *  so nothing arrives unasked. There is no numbered pager, and no loading more on scroll, which
 *  fills a large screen at once. */
export function MoreJobs({ shown, total, pageSize, hasMore, more, onMore }: MoreJobsProps) {
  const next = Math.max(1, Math.min(pageSize, total - shown));
  const label =
    more.state === "loading"
      ? "Loading more jobs"
      : more.state === "error"
        ? "Try again"
        : `Show ${fmt(next)} more ${next === 1 ? "job" : "jobs"}`;

  return (
    <div className="more">
      {more.state === "error" && (
        <p className="more-error" role="alert">
          Could not load more jobs. {more.message}
        </p>
      )}
      {hasMore ? (
        <button type="button" className="btn" disabled={more.state === "loading"} onClick={onMore}>
          {label}
        </button>
      ) : (
        <p className="more-end">End of the list</p>
      )}
      <p className="more-count" aria-live="polite">
        {fmt(shown)} of {fmt(total)} shown
      </p>
    </div>
  );
}
