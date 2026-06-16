import { useState, useEffect } from "react";
import api from "../api/client";

export interface Filters {
  fiscal_year?: number;
  version_id?: string;
  division?: string;
  brand?: string;
  channel_type?: string;
  key_account?: string;
}

export function usePlanSummary(filters: Filters) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: any = {};
    if (filters.fiscal_year) params.fiscal_year = filters.fiscal_year;
    if (filters.version_id) params.version_id = filters.version_id;
    if (filters.division) params.division = filters.division;
    if (filters.channel_type) params.channel_type = filters.channel_type;

    api.get("/api/plan/summary", { params })
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [filters.fiscal_year, filters.version_id, filters.division, filters.channel_type]);

  return { data, loading };
}

export function useVersionCompare(fiscal_year: number, division?: string) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: any = { fiscal_year };
    if (division) params.division = division;
    api.get("/api/plan/version-compare", { params })
      .then(r => setData(r.data))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [fiscal_year, division]);

  return { data, loading };
}
