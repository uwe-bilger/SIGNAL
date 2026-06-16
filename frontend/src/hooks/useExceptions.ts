import { useState, useEffect } from "react";
import api from "../api/client";
import { Filters } from "./usePlan";

export function useExceptions(filters: Filters) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: any = {};
    if (filters.fiscal_year) params.fiscal_year = filters.fiscal_year;
    if (filters.version_id) params.version_id = filters.version_id;
    if (filters.division) params.division = filters.division;
    api.get("/api/exceptions", { params })
      .then(r => setData(r.data))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.version_id, filters.division]);

  return { data, loading };
}
