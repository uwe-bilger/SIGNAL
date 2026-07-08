import React from "react";

// TASK_09: versions are derived labels — Budget (December snapshot) and
// LE01..LE11 (Jan..Nov snapshots). There is no stored version column.
const VERSION_COLORS: Record<string, string> = {
  Budget: "bg-primary/10 text-primary border-primary/30",
};

export function VersionBadge({ version }: { version: string }) {
  const cls =
    VERSION_COLORS[version] ||
    (version?.startsWith("LE")
      ? "bg-warning/10 text-warning border-warning/30"
      : "bg-surface text-text-secondary border-border");
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${cls}`}>
      {version}
    </span>
  );
}
