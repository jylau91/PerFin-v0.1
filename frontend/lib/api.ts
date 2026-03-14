const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Statement {
  id: number;
  bank: string;
  account_type: string;
  period_start: string | null;
  period_end: string | null;
  filename: string;
  uploaded_at: string;
  transaction_count: number;
}

export interface Transaction {
  id: number;
  statement_id: number;
  date: string;
  description: string;
  amount: number;
  balance: number | null;
  polarity: string | null;
  category: string;
  raw_category: string | null;
  reviewed: boolean;
}

export interface CategorySummary {
  category: string;
  total: number;
  count: number;
}

export interface AnalysisSummary {
  period_start: string | null;
  period_end: string | null;
  total_spend: number;
  total_income: number;
  by_category: CategorySummary[];
}

export interface MonthlySummary {
  month: string;
  total: number;
  by_category: CategorySummary[];
}

export interface TopMerchant {
  description: string;
  total: number;
  count: number;
}

export interface UploadResult {
  statement: Statement;
  transactions_parsed: number;
  transactions_categorised: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  uploadStatement: (file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResult>("/statements", { method: "POST", body: form });
  },

  listStatements: (): Promise<Statement[]> =>
    request<Statement[]>("/statements"),

  deleteStatement: (id: number): Promise<void> =>
    request<void>(`/statements/${id}`, { method: "DELETE" }),

  listTransactions: (params?: {
    statement_id?: number;
    category?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  }): Promise<Transaction[]> => {
    const q = new URLSearchParams();
    if (params?.statement_id != null) q.set("statement_id", String(params.statement_id));
    if (params?.category) q.set("category", params.category);
    if (params?.date_from) q.set("date_from", params.date_from);
    if (params?.date_to) q.set("date_to", params.date_to);
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    return request<Transaction[]>(`/transactions?${q.toString()}`);
  },

  updateCategory: (id: number, category: string): Promise<Transaction> =>
    request<Transaction>(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),

  getSummary: (params?: {
    date_from?: string;
    date_to?: string;
  }): Promise<AnalysisSummary> => {
    const q = new URLSearchParams();
    if (params?.date_from) q.set("date_from", params.date_from);
    if (params?.date_to) q.set("date_to", params.date_to);
    return request<AnalysisSummary>(`/analysis/summary?${q.toString()}`);
  },

  getMonthly: (months = 6): Promise<MonthlySummary[]> =>
    request<MonthlySummary[]>(`/analysis/monthly?months=${months}`),

  getTopMerchants: (limit = 10): Promise<TopMerchant[]> =>
    request<TopMerchant[]>(`/analysis/top-merchants?limit=${limit}`),
};
