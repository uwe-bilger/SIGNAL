import React from "react";

interface Props {
  stockRisk?: boolean;
  overrideFlag?: boolean;
  isNewSku?: boolean;
}

export function ExceptionBadge({ stockRisk, overrideFlag, isNewSku }: Props) {
  return (
    <span className="inline-flex gap-1">
      {stockRisk && (
        <span className="bg-danger/10 text-danger border border-danger/30 text-xs px-1.5 py-0.5 rounded-full">
          Stock Risk
        </span>
      )}
      {overrideFlag && (
        <span className="bg-warning/10 text-warning border border-warning/30 text-xs px-1.5 py-0.5 rounded-full">
          Override
        </span>
      )}
      {isNewSku && (
        <span className="bg-primary/10 text-primary border border-primary/30 text-xs px-1.5 py-0.5 rounded-full">
          New SKU
        </span>
      )}
    </span>
  );
}
