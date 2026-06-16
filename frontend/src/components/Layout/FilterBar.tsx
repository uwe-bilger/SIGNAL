import React from "react";
import { Dimensions } from "../../hooks/useDimensions";
import { Filters } from "../../hooks/usePlan";

interface Props {
  dimensions: Dimensions | null;
  filters: Filters;
  onChange: (f: Filters) => void;
}

function Select({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-text-secondary text-xs font-medium uppercase tracking-wider">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="bg-surface border border-border text-text-primary text-sm rounded-lg px-3 py-1.5 min-w-[130px] focus:outline-none focus:border-primary"
      >
        <option value="">All</option>
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export function FilterBar({ dimensions, filters, onChange }: Props) {
  const set = (key: keyof Filters) => (val: string) =>
    onChange({ ...filters, [key]: val || undefined });

  const fiscalYears = dimensions?.fiscal_years.map(y => ({ value: String(y), label: String(y) })) || [];
  const versions = dimensions?.versions
    .filter(v => v.is_financial)
    .map(v => ({ value: v.version_id, label: v.version_id })) || [];
  const divisions = dimensions?.divisions.map(d => ({ value: d.division_id, label: d.division_name })) || [];
  const channelTypes = dimensions?.channel_types.map(c => ({ value: c.channel_type_id, label: c.channel_type_name })) || [];

  return (
    <div className="flex flex-wrap gap-4 items-end px-6 py-3 bg-surface border-b border-border">
      <Select
        label="Fiscal Year"
        value={String(filters.fiscal_year || "")}
        onChange={v => onChange({ ...filters, fiscal_year: v ? Number(v) : undefined })}
        options={fiscalYears}
      />
      <Select
        label="Version"
        value={filters.version_id || ""}
        onChange={set("version_id")}
        options={versions}
      />
      <Select
        label="Division"
        value={filters.division || ""}
        onChange={set("division")}
        options={divisions}
      />
      <Select
        label="Channel Type"
        value={filters.channel_type || ""}
        onChange={set("channel_type")}
        options={channelTypes}
      />
      <button
        onClick={() => onChange({ fiscal_year: 2024, version_id: "LATEST_EST" })}
        className="text-text-secondary text-xs border border-border rounded-lg px-3 py-1.5 hover:border-primary hover:text-primary transition-colors self-end"
      >
        Clear
      </button>
    </div>
  );
}
