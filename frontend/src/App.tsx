import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Layout/Sidebar";
import { MobileNav } from "./components/Layout/Header";
import { FilterBar } from "./components/Layout/FilterBar";
import { useDimensions } from "./hooks/useDimensions";
import { Filters } from "./hooks/usePlan";
import { Act1_CurrentState } from "./pages/Act1_CurrentState";
import { Act2_Challenger } from "./pages/Act2_Challenger";
import { Act3_Reconciliation } from "./pages/Act3_Reconciliation";
import { Act4_Acquisition } from "./pages/Act4_Acquisition";

const DEFAULT_FILTERS: Filters = { fiscal_year: 2024, version_id: "LATEST_EST" };

function App() {
  const { data: dimensions } = useDimensions();
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-bg font-sans">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <FilterBar dimensions={dimensions} filters={filters} onChange={setFilters} />
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<Act1_CurrentState filters={filters} />} />
              <Route path="/challenger" element={<Act2_Challenger filters={filters} />} />
              <Route path="/reconciliation" element={<Act3_Reconciliation filters={filters} />} />
              <Route path="/acquisition" element={<Act4_Acquisition filters={filters} />} />
            </Routes>
          </main>
        </div>
        <MobileNav />
      </div>
    </BrowserRouter>
  );
}

export default App;
