import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Layout/Sidebar";
import { MobileNav } from "./components/Layout/Header";
import { FilterBar } from "./components/Layout/FilterBar";
import { useDimensions } from "./hooks/useDimensions";
import { Filters } from "./hooks/usePlan";
import { Act1CurrentState } from "./pages/Act1CurrentState";
import { Act2Challenger } from "./pages/Act2Challenger";
import { Act3Reconciliation } from "./pages/Act3Reconciliation";
import { Act4Acquisition } from "./pages/Act4Acquisition";

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
              <Route path="/" element={<Act1CurrentState filters={filters} />} />
              <Route path="/challenger" element={<Act2Challenger filters={filters} />} />
              <Route path="/reconciliation" element={<Act3Reconciliation filters={filters} />} />
              <Route path="/acquisition" element={<Act4Acquisition filters={filters} />} />
            </Routes>
          </main>
        </div>
        <MobileNav />
      </div>
    </BrowserRouter>
  );
}

export default App;
