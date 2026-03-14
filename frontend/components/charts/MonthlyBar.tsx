"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import type { MonthlySummary } from "@/lib/api";

interface Props {
  data: MonthlySummary[];
}

export default function MonthlyBar({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        No monthly data
      </div>
    );
  }

  const chartData = data.map((d) => ({
    month: d.month.slice(5), // "MM"
    total: d.total,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="month" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false}
          tickFormatter={(v) => `$${v}`} width={50} />
        <Tooltip
          formatter={(v: number) => [`S$${v.toFixed(2)}`, "Spend"]}
          contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }}
          labelStyle={{ color: "#f1f5f9" }}
        />
        <Bar dataKey="total" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
