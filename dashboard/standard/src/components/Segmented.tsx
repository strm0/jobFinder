import { useLayoutEffect, useRef, type ReactNode } from "react";

export interface SegmentOption<T extends string> {
  id: T;
  label: ReactNode;
  title?: string;
}

interface SegmentedProps<T extends string> {
  label: string;
  options: SegmentOption<T>[];
  value: T;
  /** Views mark the chosen option as the current page; filters mark it as pressed. */
  mark?: "pressed" | "page";
  onChange: (value: T) => void;
}

/** A pill track with a white thumb that slides to the chosen option. */
export function Segmented<T extends string>({ label, options, value, mark = "pressed", onChange }: SegmentedProps<T>) {
  const trackRef = useRef<HTMLDivElement>(null);

  // The thumb takes the chosen button's place and width by measuring it, so it fits any label, a
  // count that comes and goes, and the font arriving. It only glides once the fonts are in, so the
  // page does not open with a slide.
  useLayoutEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const chosen = track.querySelector<HTMLElement>("[data-chosen]");
    // Nothing is chosen here when the current view sits in the toolbar's other slider. The thumb is
    // hidden, and the glide is off until the thumb is placed again, so it reappears on its option
    // rather than sliding over from where it last stood.
    if (!chosen) {
      track.removeAttribute("data-ready");
      return;
    }
    // The track's width runs to the end of its last option, not scrollWidth, which would count the
    // thumb itself and never shrink.
    const last = track.querySelector<HTMLElement>("button:last-of-type");
    const place = () => {
      track.style.setProperty("--thumb-x", `${chosen.offsetLeft}px`);
      track.style.setProperty("--thumb-w", `${chosen.offsetWidth}px`);
      if (last) {
        const end = last.offsetLeft + last.offsetWidth + parseFloat(getComputedStyle(track).paddingRight);
        track.style.setProperty("--track-w", `${end}px`);
      }
    };
    place();

    // On a phone the track can be narrower than its options, so the chosen one is kept in view.
    const start = chosen.offsetLeft;
    const end = start + chosen.offsetWidth;
    if (start < track.scrollLeft) track.scrollLeft = start - 3;
    else if (end > track.scrollLeft + track.clientWidth) track.scrollLeft = end - track.clientWidth + 3;

    const observer = new ResizeObserver(place);
    track.querySelectorAll("button").forEach((button) => observer.observe(button));
    let alive = true;
    void document.fonts.ready.then(() => {
      if (alive) requestAnimationFrame(() => track.setAttribute("data-ready", ""));
    });
    return () => {
      alive = false;
      observer.disconnect();
    };
  }, [value]);

  return (
    <div
      className="segmented"
      ref={trackRef}
      role="group"
      aria-label={label}
      data-empty={options.every((option) => option.id !== value) || undefined}
    >
      <span className="segmented-thumb" aria-hidden="true" />
      {options.map((option) => {
        const chosen = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            className="segment"
            data-chosen={chosen || undefined}
            aria-pressed={mark === "pressed" ? chosen : undefined}
            aria-current={mark === "page" && chosen ? "page" : undefined}
            title={option.title}
            onClick={() => {
              if (!chosen) onChange(option.id);
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
