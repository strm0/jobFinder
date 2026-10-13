import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { fmt } from "../format";
import type { Lane } from "../types";

interface LanePickerProps {
  lanes: Lane[];
  selected: string;
  onSelect: (code: string) => void;
}

/** The lanes as one scrolling row of chips, with arrows on whichever side has more. */
export function LanePicker({ lanes, selected, onSelect }: LanePickerProps) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ left: false, right: false });

  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;
    const update = () =>
      setEdges({
        left: row.scrollLeft > 1,
        right: row.scrollLeft + row.clientWidth < row.scrollWidth - 1,
      });
    update();
    row.addEventListener("scroll", update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(row);
    return () => {
      row.removeEventListener("scroll", update);
      observer.disconnect();
    };
  }, [lanes]);

  // The chosen lane is always in view, including one remembered from the last visit.
  useEffect(() => {
    rowRef.current
      ?.querySelector<HTMLElement>('[aria-pressed="true"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [selected]);

  const scroll = (direction: 1 | -1) => {
    const row = rowRef.current;
    if (!row) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    row.scrollBy({ left: direction * row.clientWidth * 0.7, behavior: reduced ? "auto" : "smooth" });
  };

  return (
    <div className="shell lane-bar" data-left={edges.left || undefined} data-right={edges.right || undefined}>
      <div className="lane-row" ref={rowRef} role="group" aria-label="Choose a lane">
        {lanes.map((lane) => (
          <button
            key={lane.code}
            type="button"
            className="lane-chip"
            aria-pressed={lane.code === selected}
            title={lane.name}
            onClick={() => onSelect(lane.code)}
          >
            <span className="lane-code">{lane.code}</span>
            <span className="lane-name">{lane.name}</span>
            <span className="lane-count">{fmt(lane.count)}</span>
            {lane.newCount > 0 && <span className="lane-new">{fmt(lane.newCount)} new</span>}
          </button>
        ))}
      </div>
      {edges.left && (
        <button
          type="button"
          className="icon-btn lane-scroll lane-scroll-left"
          aria-label="Show earlier lanes"
          tabIndex={-1}
          onClick={() => scroll(-1)}
        >
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
      )}
      {edges.right && (
        <button
          type="button"
          className="icon-btn lane-scroll lane-scroll-right"
          aria-label="Show more lanes"
          tabIndex={-1}
          onClick={() => scroll(1)}
        >
          <ChevronRight size={18} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
