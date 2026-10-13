import { Check, Globe, MapPin, Star, Undo2, X } from "lucide-react";
import { fmt, placeShort } from "../format";
import type { Job } from "../types";

interface JobCardProps {
  job: Job;
  selected: boolean;
  onOpen: () => void;
  onStar: () => void;
  onRemove: () => void;
  onRestore: () => void;
}

/** One job as a card: a head band with the score and the x, what a scan needs below it, and the
 *  lane, standing and star in a footer. Opening it fills the panel beside the grid. A card is as
 *  tall as the longest card in its row. The x sits top right and the star bottom right. A card
 *  carries no closing date. */
export function JobCard({ job, selected, onOpen, onStar, onRemove, onRestore }: JobCardProps) {
  const titleId = `card-${job.id}-title`;
  const lanes = [...job.lanes].sort((a, b) => (b.fit ?? 0) - (a.fit ?? 0));
  const lead = lanes[0];

  return (
    <article
      className="card"
      id={`card-${job.id}`}
      data-selected={selected || undefined}
      data-closed={job.closed || undefined}
      aria-labelledby={titleId}
      style={{ viewTransitionName: `card-${job.id}` }}
    >
      <div className="card-head">
        <p className="card-score">
          <span className="score-value">{job.score === null ? "n/a" : job.score.toFixed(1)}</span>
          <span className="score-label">score</span>
          {job.isNew && <span className="badge badge-new">New</span>}
        </p>
        {/* A removed job offers Restore in the x's place. An applied job cannot be removed, so it has neither. */}
        {job.dismissed ? (
          <button
            type="button"
            className="btn btn-small card-restore"
            aria-label={`Restore ${job.title}`}
            onClick={onRestore}
          >
            <Undo2 size={14} aria-hidden="true" />
            Restore
          </button>
        ) : (
          !job.applied && (
            <button
              type="button"
              className="icon-btn card-remove"
              aria-label={`Remove ${job.title}`}
              title="Remove"
              onClick={onRemove}
            >
              <X size={18} aria-hidden="true" />
            </button>
          )
        )}
      </div>

      <h3 className="card-title" id={titleId}>
        <button
          type="button"
          className="card-open"
          aria-expanded={selected}
          aria-controls={selected ? "job-panel" : undefined}
          onClick={onOpen}
        >
          {job.title}
        </button>
      </h3>
      <p className="card-employer">{job.employer ?? "Employer not stated"}</p>
      <p className="card-place">
        <MapPin size={14} aria-hidden="true" />
        <span>{placeShort(job.city, job.otherCities)}</span>
      </p>
      {/* An ad from another job site says which. A Platsbanken ad carries no tag. */}
      {job.site && (
        <p className="card-place card-source">
          <Globe size={14} aria-hidden="true" />
          <span>via {job.site}</span>
        </p>
      )}
      {job.summary && <p className="card-summary">{job.summary}</p>}

      <div className="card-foot">
        {lead && (
          <ul className="card-lanes" aria-label="Lanes" title={lanes.map((l) => `${l.code} ${l.name}`).join(", ")}>
            <li className="lane-tag">
              <span className="lane-tag-code">{lead.code}</span> {lead.short || lead.name}
            </li>
            {lanes.length > 1 && <li className="lane-tag">+{lanes.length - 1}</li>}
          </ul>
        )}
        <p className="card-meta">
          {job.closed && <span className="badge badge-closed">Closed</span>}
          {job.hasApplication && (
            <span className="card-brief" title="A brief is written for this job">
              <Check size={14} aria-hidden="true" />
              Brief
            </span>
          )}
          {job.rank !== null && <span className="card-rank">#{fmt(job.rank)}</span>}
          {/* A job is saved or applied, never both, so an applied job carries the mark in the star's
              place. A removed job shows neither until it is restored. */}
          {job.applied ? (
            <span className="badge">Applied</span>
          ) : (
            !job.dismissed && (
              <button
                type="button"
                className="icon-btn star"
                aria-pressed={job.starred}
                aria-label={job.starred ? `Remove ${job.title} from saved` : `Save ${job.title}`}
                title={job.starred ? "Remove from saved" : "Save"}
                onClick={onStar}
              >
                <Star size={18} aria-hidden="true" />
              </button>
            )
          )}
        </p>
      </div>
    </article>
  );
}
