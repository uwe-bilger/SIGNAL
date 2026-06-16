import React from "react";

const VERSION_COLORS: Record<string, string> = {
  BUDGET: "bg-primary/10 text-primary border-primary/30",
  OP_PLAN: "bg-primary/10 text-primary border-primary/30",
  LE1: "bg-warning/10 text-warning border-warning/30",
  LE2: "bg-warning/10 text-warning border-warning/30",
  LE3: "bg-warning/10 text-warning border-warning/30",
  LATEST_EST: "bg-success/10 text-success border-success/30",
};

export function VersionBadge({ version }: { version: string }) {
  const cls = VERSION_COLORS[version] || "bg-surface text-text-secondary border-border";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${cls}`}>
      {version.replace("_", " ")}
    </span>
  );
}
