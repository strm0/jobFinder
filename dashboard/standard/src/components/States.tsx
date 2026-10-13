import type { ReactNode } from "react";
import { CircleAlert, TriangleAlert } from "lucide-react";

interface NoticeProps {
  title: string;
  children: ReactNode;
  tone?: "warning" | "error";
  action?: ReactNode;
}

export function Notice({ title, children, tone = "warning", action }: NoticeProps) {
  const Icon = tone === "error" ? CircleAlert : TriangleAlert;
  return (
    <div className="notice" data-tone={tone} role={tone === "error" ? "alert" : "status"}>
      <Icon size={20} aria-hidden="true" />
      <div className="notice-body">
        <p className="notice-title">{title}</p>
        <p className="notice-text">{children}</p>
      </div>
      {action}
    </div>
  );
}

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ icon, title, children, action }: EmptyStateProps) {
  return (
    <div className="empty">
      <span className="empty-icon" aria-hidden="true">
        {icon}
      </span>
      <h2 className="empty-title">{title}</h2>
      <p className="empty-text">{children}</p>
      {action}
    </div>
  );
}

export function SkeletonGrid() {
  return (
    <div className="grid" role="status">
      <span className="sr-only">Loading jobs</span>
      {Array.from({ length: 8 }, (_, i) => (
        <div className="skeleton-card" key={i} aria-hidden="true">
          <span className="bone bone-title" />
          <span className="bone bone-title bone-short" />
          <span className="bone bone-line" />
          <span className="bone bone-line bone-short" />
          <span className="bone bone-line" />
        </div>
      ))}
    </div>
  );
}
