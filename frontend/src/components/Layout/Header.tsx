import React from "react";
import { NavLink } from "react-router-dom";

const ACTS = [
  { path: "/", label: "Current State" },
  { path: "/challenger", label: "Challenger" },
  { path: "/reconciliation", label: "Reconciliation" },
  { path: "/acquisition", label: "M&A" },
];

export function MobileNav() {
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-border z-50">
      <div className="flex">
        {ACTS.map((act, i) => (
          <NavLink
            key={act.path}
            to={act.path}
            end={act.path === "/"}
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-xs transition-colors ` +
              (isActive ? "text-primary" : "text-text-secondary")
            }
          >
            <div className="font-medium">Act {i + 1}</div>
            <div className="text-xs opacity-70">{act.label}</div>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
