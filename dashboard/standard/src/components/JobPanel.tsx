import { useState, type Ref } from "react";
import { Check, ChevronLeft, Copy, ExternalLink, MapPin, Send, Star, Undo2, X } from "lucide-react";
import { employmentLabel, formatDate, formatDay, placeFull } from "../format";
import type { BriefState, Job } from "../types";

const FIT: Record<number, string> = { 3: "Strong fit", 2: "Good fit", 1: "Some fit" };

interface JobPanelProps {
  job: Job;
  brief: BriefState | undefined;
  titleRef: Ref<HTMLHeadingElement>;
  onClose: () => void;
  onStar: () => void;
  onBrief: () => void;
  onApplied: () => void;
  onRestore: () => void;
}

/** The chosen job beside the grid: when to apply, why it scored, the three actions, and Mark
 *  applied at the bottom. A removed job has Restore in place of Save and no Mark applied, so it
 *  is restored before anything else is done with it. */
export function JobPanel({ job, brief, titleRef, onClose, onStar, onBrief, onApplied, onRestore }: JobPanelProps) {
  const working = brief?.state === "working";
  return (
    <aside className="panel" id="job-panel" aria-labelledby="panel-title" style={{ viewTransitionName: "job-panel" }}>
      <div className="panel-bar">
        <button type="button" className="btn btn-quiet panel-back" onClick={onClose}>
          <ChevronLeft size={18} aria-hidden="true" />
          All jobs
        </button>
        <button type="button" className="icon-btn panel-close" aria-label="Close the job details" title="Close (Esc)" onClick={onClose}>
          <X size={20} aria-hidden="true" />
        </button>
      </div>

      <div className="panel-body">
        <div>
          <p className="panel-employer-name">{job.employer ?? "Employer not stated"}</p>
          <p className="panel-place">
            <MapPin size={14} aria-hidden="true" />
            <span>{placeFull(job.city, job.otherCities)}</span>
          </p>
        </div>

        <h2 className="panel-title" id="panel-title" tabIndex={-1} ref={titleRef}>
          {job.title}
        </h2>

        {(job.isNew || job.closed || job.employmentType || job.site) && (
          <div className="panel-tags">
            {job.isNew && <span className="badge badge-new">New</span>}
            {job.closed && <span className="badge badge-closed">Closed</span>}
            {job.employmentType && <span className="badge">{employmentLabel(job.employmentType)}</span>}
            {job.site && (
              <a className="badge badge-link" href={job.url} target="_blank" rel="noopener noreferrer">
                via {job.site}
                <ExternalLink size={12} aria-hidden="true" />
              </a>
            )}
          </div>
        )}

        <dl className="panel-facts">
          <div>
            <dt>Apply by</dt>
            <dd>{job.applyBy ? formatDate(job.applyBy) : "Not stated"}</dd>
          </div>
          <div>
            <dt>Score</dt>
            <dd className="num">{job.score === null ? "n/a" : job.score.toFixed(1)}</dd>
          </div>
          {job.rank !== null && (
            <div>
              <dt>Place in this list</dt>
              <dd className="num">#{job.rank}</dd>
            </div>
          )}
          {job.applied && job.appliedAt && (
            <div>
              <dt>Applied</dt>
              <dd>{formatDay(job.appliedAt)}</dd>
            </div>
          )}
        </dl>

        {/* One brief serves both /cv and /letter, so one button writes it. A button for the CV and
            another for the cover letter would both write the same brief. */}
        <div className="panel-actions">
          <div className="panel-actions-row">
            <button type="button" className="btn btn-primary" disabled={working} onClick={onBrief}>
              Write brief
            </button>
            <a className="btn" href={job.url} target="_blank" rel="noopener noreferrer">
              Open posting
              <ExternalLink size={16} aria-hidden="true" />
            </a>
            {job.dismissed ? (
              <button type="button" className="btn" onClick={onRestore}>
                <Undo2 size={16} aria-hidden="true" />
                Restore
              </button>
            ) : (
              !job.applied && (
                <button type="button" className="btn" aria-pressed={job.starred} onClick={onStar}>
                  <Star size={16} aria-hidden="true" />
                  {job.starred ? "Saved" : "Save"}
                </button>
              )
            )}
          </div>
        </div>

        {job.hasApplication && !brief && (
          <p className="panel-note">
            <Check size={16} aria-hidden="true" />
            An application folder already exists for this job.
          </p>
        )}
        {brief && <BriefNote brief={brief} />}

        <section className="panel-section" aria-labelledby="why-title">
          <h3 id="why-title">Why this score</h3>
          <div className="why">
            <Reason label="Want" value={job.want} text={job.wantWhy} />
            <Reason label="Reach" value={job.reach} text={job.reachWhy} />
          </div>
        </section>

        {job.summary && (
          <section className="panel-section" aria-labelledby="summary-title">
            <h3 id="summary-title">Summary</h3>
            <p className="panel-summary">{job.summary}</p>
          </section>
        )}

        {job.lanes.length > 0 && (
          <section className="panel-section" aria-labelledby="lanes-title">
            <h3 id="lanes-title">Lanes</h3>
            <ul className="panel-lanes">
              {job.lanes.map((lane) => (
                <li key={lane.code}>
                  <span className="panel-lane-code">{lane.code}</span>
                  <span className="panel-lane-name">{lane.name}</span>
                  {lane.fit !== null && <span className="fit">{FIT[lane.fit] ?? `Fit ${lane.fit}`}</span>}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* At the bottom of the details. Pressed again, it undoes the mark. */}
        {!job.dismissed && (
          <div className="panel-section">
            <button type="button" className="btn" aria-pressed={job.applied} onClick={onApplied}>
              <Send size={16} aria-hidden="true" />
              {job.applied ? "Applied" : "Mark applied"}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

function Reason({ label, value, text }: { label: string; value: number | null; text: string | null }) {
  return (
    <div className="why-row">
      <p className="why-head">
        <span className="why-label">{label}</span>
        <span className="why-value">
          {value ?? "n/a"}
          <span className="why-of"> of 10</span>
        </span>
      </p>
      <p className="why-text">{text ?? "No reason recorded."}</p>
    </div>
  );
}

function BriefNote({ brief }: { brief: BriefState }) {
  if (brief.state === "working") {
    return (
      <p className="brief-note" role="status">
        Writing the brief…
      </p>
    );
  }
  if (brief.state === "error") {
    return (
      <div className="brief-note" data-tone="error" role="alert">
        <p>
          <strong>The brief was not written.</strong> {brief.message}
        </p>
      </div>
    );
  }
  return (
    <div className="brief-note" role="status">
      <p>
        <strong>{brief.state === "created" ? "Brief written" : "Already there"}</strong>{" "}
        <code>{brief.path}</code>
        {brief.state === "exists" && ", so nothing was overwritten"}.
      </p>
      <p>Next, open Claude Code in that folder:</p>
      <CopyCommand command={brief.command} />
      <p>Then run:</p>
      <CopyCommand command="/cv" />
      <CopyCommand command="/letter" />
    </div>
  );
}

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard access refused: the command stays on screen to copy by hand.
    }
  };
  return (
    <div className="copy">
      <code>{command}</code>
      <button type="button" className="btn btn-small" aria-label={copied ? `Copied ${command}` : `Copy ${command}`} onClick={copy}>
        {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}
