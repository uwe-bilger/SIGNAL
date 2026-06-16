import { useState, useEffect } from "react";
import api from "../api/client";

export interface Dimensions {
  divisions: { division_id: string; division_name: string }[];
  brands: { brand_id: string; brand_name: string; division_id: string }[];
  categories: { category_id: string; category_name: string }[];
  channel_types: { channel_type_id: string; channel_type_name: string }[];
  markets: { market_id: string; market_name: string }[];
  key_accounts: { key_account_id: string; key_account_name: string; channel_type_id: string }[];
  versions: { version_id: string; version_order: number; is_financial: boolean }[];
  fiscal_years: number[];
}

export function useDimensions() {
  const [data, setData] = useState<Dimensions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/dimensions")
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
