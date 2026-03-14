"use client";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { CategorySummary } from "@/lib/api";

const COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#a3e635", "#94a3b8",
];

interface Props {
  data: CategorySummary[];
}

export default function SpendingDonut({ data }: Props) {
  const filtered = data.filter((d) => d.category !== "Income" && d.total > 0);

  if (filtered.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        No spending data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={filtered}
          dataKey="total"
          nameKey="category"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={2}
        >
          {filtered.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(val: number) => [`S$${val.toFixed(2)}`, ""]}
          contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }}
          labelStyle={{ color: "#f1f5f9" }}
        />
        <Legend
          formatter={(value) => (
            <span className="text-xs text-slate-300">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
