import React from "react";

interface Props {
  biasFlag?: boolean;
  accuracyFlag?: boolean;
  isNewSku?: boolean;
}

export function ExceptionBadge({ biasFlag, accuracyFlag, isNewSku }: Props) {
  return (
    <span className="inline-flex gap-1">
      {accuracyFlag && (
        <span className="bg-danger/10 text-danger border border-danger/30 text-xs px-1.5 py-0.5 rounded-full">
          Low Accuracy
        </span>
      )}
      {biasFlag && (
        <span className="bg-warning/10 text-warning border border-warning/30 text-xs px-1.5 py-0.5 rounded-full">
          Bias
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
