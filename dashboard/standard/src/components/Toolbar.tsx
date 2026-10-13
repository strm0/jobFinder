import { fmt } from "../format";
import type { Place, Source, ViewId } from "../types";
import { Segmented } from "./Segmented";

// Two sliders: the lists the system ranks, then the user's own.
const LISTS: { id: ViewId; label: string }[] = [
  { id: "top", label: "Top picks" },
  { id: "lanes", label: "By lane" },
  { id: "phd", label: "PhD" },
  { id: "rejected", label: "Rejected" },
];

// The user's own lists. Removed holds what was taken off the other lists, until the next run.
const MINE: { id: ViewId; label: string }[] = [
  { id: "favourites", label: "Saved" },
  { id: "applied", label: "Applied" },
  { id: "dismissed", label: "Removed" },
];

const PLACES: { id: Place; label: string; title: string }[] = [
  { id: "all", label: "All", title: "Everywhere" },
  { id: "stockholm", label: "Stockholm", title: "Stockholm county, and ads that give no place" },
  { id: "outside", label: "Outside", title: "Outside Stockholm county, and ads that give no place" },
];

// Where the jobs come from. The ads from other job sites are mixed into every list with a tag,
// and this shows only Platsbanken's or only theirs.
const SOURCES: { id: Source; label: string; title: string }[] = [
  { id: "all", label: "All sites", title: "Platsbanken and the other job sites" },
  { id: "platsbanken", label: "Platsbanken", title: "Only jobs from Platsbanken" },
  { id: "other", label: "Other sites", title: "Only jobs from other job sites, such as thehub.io and studentjob.se" },
];

interface ToolbarProps {
  view: ViewId;
  favourites: number;
  applied: number;
  dismissed: number;
  place: Place;
  source: Source;
  onlyNew: boolean;
  newCount: number | null;
  onView: (view: ViewId) => void;
  onPlace: (place: Place) => void;
  onSource: (source: Source) => void;
  onNew: (onlyNew: boolean) => void;
}

/** Two sliders of views on the left, the lists the system ranks and then the user's own, and New, the
 *  place and the source on the right, which apply to every view. One view is chosen at a time, so
 *  the slider without it shows no thumb. */
export function Toolbar({
  view,
  favourites,
  applied,
  dismissed,
  place,
  source,
  onlyNew,
  newCount,
  onView,
  onPlace,
  onSource,
  onNew,
}: ToolbarProps) {
  const counts: Partial<Record<ViewId, number>> = { favourites, applied, dismissed };
  const mine = MINE.map((v) => {
    const n = counts[v.id] ?? 0;
    return {
      id: v.id,
      label:
        n > 0 ? (
          <>
            {v.label}{" "}
            <span className="segment-count">{fmt(n)}</span>
          </>
        ) : (
          v.label
        ),
    };
  });

  return (
    <div className="shell toolbar">
      <nav className="toolbar-views" aria-label="Views">
        <Segmented label="Lists" mark="page" options={LISTS} value={view} onChange={onView} />
        <Segmented label="Your jobs" mark="page" options={mine} value={view} onChange={onView} />
      </nav>
      <div className="toolbar-controls">
        <button
          type="button"
          className="chip chip-new"
          aria-pressed={onlyNew}
          title="Only the jobs from every run since you last looked"
          onClick={() => onNew(!onlyNew)}
        >
          <span className="new-dot" aria-hidden="true" />
          New
          {newCount !== null && <span className="chip-count">{fmt(newCount)}</span>}
        </button>
        <Segmented label="Where" options={PLACES} value={place} onChange={onPlace} />
        <Segmented label="Source" options={SOURCES} value={source} onChange={onSource} />
      </div>
    </div>
  );
}
