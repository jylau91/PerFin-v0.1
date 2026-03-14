"use client";
import { useEffect, useState } from "react";
import { TrendingDown, TrendingUp, Receipt, Layers, Upload } from "lucide-react";
import Link from "next/link";
import { api, type AnalysisSummary, type MonthlySummary, type TopMerchant } from "@/lib/api";
import SpendingDonut from "@/components/charts/SpendingDonut";
import MonthlyBar from "@/components/charts/MonthlyBar";

const CATEGORY_EMOJI: Record<string, string> = {
  "Food & Drink": "🍜", Transport: "🚌", Shopping: "🛍️", Groceries: "🛒",
  Healthcare: "🏥", Entertainment: "🎬", "Bills & Utilities": "💡",
  Travel: "✈️", Education: "📚", Income: "💰", Other: "📦",
};

function KpiCard({ label, value, icon, sub, colour }: {
  label: string; value: string; icon: React.ReactNode; sub?: string; colour: string;
}) {
  return (
    <div className="bg-slate-800 rounded-xl p-5 flex items-start gap-4">
      <div className={`${colour} p-2.5 rounded-lg shrink-0`}>{icon}</div>
      <div>
        <p className="text-slate-400 text-xs font-medium">{label}</p>
        <p className="text-white text-2xl font-bold mt-0.5">{value}</p>
        {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [monthly, setMonthly] = useState<MonthlySummary[]>([]);
  const [merchants, setMerchants] = useState<TopMerchant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getSummary(), api.getMonthly(6), api.getTopMerchants(5)])
      .then(([s, m, top]) => {
        setSummary(s);
        setMonthly(m);
        setMerchants(top);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">Loading…</div>
    );
  }

  const isEmpty = !summary || summary.by_category.length === 0;

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center h-80 gap-4">
        <Layers size={48} className="text-slate-600" />
        <p className="text-slate-400 text-lg font-medium">No data yet</p>
        <p className="text-slate-500 text-sm">Upload a bank statement to get started</p>
        <Link
          href="/upload"
          className="mt-2 flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          <Upload size={15} /> Upload Statement
        </Link>
      </div>
    );
  }

  const topCategory = summary.by_category.filter((c) => c.category !== "Income")[0];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <Link
          href="/upload"
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Upload size={14} /> Upload
        </Link>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          label="Total Spend"
          value={`S$${summary.total_spend.toFixed(2)}`}
          icon={<TrendingDown size={18} className="text-red-400" />}
          colour="bg-red-900/40"
        />
        <KpiCard
          label="Total Income"
          value={`S$${summary.total_income.toFixed(2)}`}
          icon={<TrendingUp size={18} className="text-emerald-400" />}
          colour="bg-emerald-900/40"
        />
        <KpiCard
          label="Top Category"
          value={topCategory?.category ?? "—"}
          icon={<Receipt size={18} className="text-blue-400" />}
          sub={topCategory ? `S$${topCategory.total.toFixed(2)}` : undefined}
          colour="bg-blue-900/40"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Spending by Category</h2>
          <SpendingDonut data={summary.by_category} />
        </div>
        <div className="bg-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Monthly Spend</h2>
          <MonthlyBar data={monthly} />
        </div>
      </div>

      {/* Category breakdown + Top merchants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Category Breakdown</h2>
          <div className="space-y-2">
            {summary.by_category
              .filter((c) => c.category !== "Income")
              .slice(0, 8)
              .map((cat) => (
                <div key={cat.category} className="flex items-center gap-2">
                  <span className="text-base w-6">{CATEGORY_EMOJI[cat.category] ?? "📦"}</span>
                  <div className="flex-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-300">{cat.category}</span>
                      <span className="text-white font-medium">S${cat.total.toFixed(2)}</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{
                          width: `${Math.min(100, (cat.total / summary.total_spend) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Top Merchants</h2>
          {merchants.length === 0 ? (
            <p className="text-slate-500 text-sm">No data</p>
          ) : (
            <div className="space-y-2">
              {merchants.map((m, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-700 last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 truncate">{m.description}</p>
                    <p className="text-xs text-slate-500">{m.count} transactions</p>
                  </div>
                  <p className="text-sm font-semibold text-white ml-4">
                    S${m.total.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
