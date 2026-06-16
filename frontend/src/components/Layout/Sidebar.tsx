import React from "react";
import { NavLink } from "react-router-dom";

const ACTS = [
  { path: "/", label: "Act 1", sublabel: "Current State", icon: "📊" },
  { path: "/challenger", label: "Act 2", sublabel: "Challenger Pack", icon: "⚡" },
  { path: "/reconciliation", label: "Act 3", sublabel: "Reconciliation", icon: "🔄" },
  { path: "/acquisition", label: "Act 4", sublabel: "M&A Integration", icon: "🚀" },
];

export function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-56 min-h-screen bg-surface border-r border-border flex-shrink-0">
      <div className="px-6 py-5 border-b border-border">
        <div className="text-primary font-bold text-lg tracking-wide">SIGNAL</div>
        <div className="text-text-secondary text-xs mt-0.5">Demand Intelligence</div>
      </div>
      <nav className="flex-1 py-4">
        {ACTS.map(act => (
          <NavLink
            key={act.path}
            to={act.path}
            end={act.path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-3 mx-2 rounded-lg mb-1 transition-colors text-sm ` +
              (isActive
                ? "bg-primary/10 text-primary border border-primary/20"
                : "text-text-secondary hover:text-text-primary hover:bg-white/5")
            }
          >
            <span>{act.icon}</span>
            <div>
              <div className="font-medium">{act.label}</div>
              <div className="text-xs opacity-70">{act.sublabel}</div>
            </div>
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-border">
        <div className="text-text-secondary text-xs">signal.bilger.us</div>
      </div>
    </aside>
  );
}
