"use client";
import { useEffect, useState } from "react";
import { CheckCircle, Pencil, X } from "lucide-react";
import { api, type Transaction } from "@/lib/api";

const CATEGORIES = [
  "Food & Drink", "Transport", "Shopping", "Groceries", "Healthcare",
  "Entertainment", "Bills & Utilities", "Travel", "Education", "Income", "Other",
];

const CATEGORY_COLOUR: Record<string, string> = {
  "Food & Drink": "bg-orange-900/40 text-orange-300",
  Transport: "bg-blue-900/40 text-blue-300",
  Shopping: "bg-pink-900/40 text-pink-300",
  Groceries: "bg-green-900/40 text-green-300",
  Healthcare: "bg-red-900/40 text-red-300",
  Entertainment: "bg-purple-900/40 text-purple-300",
  "Bills & Utilities": "bg-yellow-900/40 text-yellow-300",
  Travel: "bg-cyan-900/40 text-cyan-300",
  Education: "bg-indigo-900/40 text-indigo-300",
  Income: "bg-emerald-900/40 text-emerald-300",
  Other: "bg-slate-700 text-slate-300",
};

function CategoryBadge({ category }: { category: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLOUR[category] ?? "bg-slate-700 text-slate-300"}`}>
      {category}
    </span>
  );
}

function EditCategoryModal({
  txn,
  onSave,
  onClose,
}: {
  txn: Transaction;
  onSave: (id: number, cat: string) => Promise<void>;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(txn.category);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await onSave(txn.id, selected);
    setSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl p-6 w-full max-w-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold">Edit Category</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={16} /></button>
        </div>
        <p className="text-slate-400 text-xs mb-4 truncate">{txn.description}</p>
        <div className="grid grid-cols-2 gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelected(cat)}
              className={`text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                selected === cat
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="mt-4 w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [editing, setEditing] = useState<Transaction | null>(null);

  const load = () => {
    setLoading(true);
    api.listTransactions({
      category: filterCat || undefined,
      date_from: filterFrom || undefined,
      date_to: filterTo || undefined,
      limit: 500,
    })
      .then(setTransactions)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async (id: number, category: string) => {
    await api.updateCategory(id, category);
    setTransactions((prev) =>
      prev.map((t) => (t.id === id ? { ...t, category, reviewed: true } : t))
    );
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Transactions</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-slate-800 rounded-xl p-4">
        <select
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value)}
          className="bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 border-0 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input
          type="date"
          value={filterFrom}
          onChange={(e) => setFilterFrom(e.target.value)}
          className="bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 border-0 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="From"
        />
        <input
          type="date"
          value={filterTo}
          onChange={(e) => setFilterTo(e.target.value)}
          className="bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 border-0 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="To"
        />
        <button
          onClick={load}
          className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Filter
        </button>
        <button
          onClick={() => { setFilterCat(""); setFilterFrom(""); setFilterTo(""); }}
          className="bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-2 rounded-lg text-sm transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Table */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-slate-500">Loading…</div>
        ) : transactions.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
            No transactions found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left px-4 py-3 text-slate-400 font-medium">Date</th>
                  <th className="text-left px-4 py-3 text-slate-400 font-medium">Description</th>
                  <th className="text-left px-4 py-3 text-slate-400 font-medium">Category</th>
                  <th className="text-right px-4 py-3 text-slate-400 font-medium">Amount</th>
                  <th className="text-center px-4 py-3 text-slate-400 font-medium">Reviewed</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{txn.date}</td>
                    <td className="px-4 py-3 text-slate-200 max-w-xs truncate">{txn.description}</td>
                    <td className="px-4 py-3">
                      <CategoryBadge category={txn.category} />
                    </td>
                    <td className={`px-4 py-3 text-right font-medium whitespace-nowrap ${
                      txn.category === "Income" ? "text-emerald-400" : "text-white"
                    }`}>
                      {txn.polarity === "CR" ? "+" : ""}S${Math.abs(txn.amount).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {txn.reviewed && <CheckCircle size={14} className="text-emerald-500 mx-auto" />}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setEditing(txn)}
                        className="text-slate-500 hover:text-slate-300 transition-colors"
                        title="Edit category"
                      >
                        <Pencil size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-slate-500 text-xs px-4 py-2">
              {transactions.length} transactions
            </p>
          </div>
        )}
      </div>

      {editing && (
        <EditCategoryModal
          txn={editing}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
