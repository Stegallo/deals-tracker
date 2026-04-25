export interface Product {
  id: string;
  name: string;
  asin: string;
  deal_price: number;
  unit_price: number;
  unit_count: number;
  unit_label: string;
  typical_unit_price?: number;
  bulk_note?: string;
  image_url?: string;
  why_good: string;
  last_checked: string;
  stale: boolean;
  current_price: number | null;
}
