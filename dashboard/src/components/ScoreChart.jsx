import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const GRADE_COLORS = {
  A: '#4ade80',
  B: '#60a5fa',
  C: '#facc15',
  D: '#fb923c',
  F: '#f87171',
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 shadow-xl">
      <p className="text-muted text-xs mb-1">{label}</p>
      <p className="text-text font-semibold">Score: {payload[0].value}</p>
    </div>
  );
}

export default function ScoreChart({ history }) {
  if (!history || history.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted text-sm">
        No history data available
      </div>
    );
  }

  const data = history.map((h) => ({
    date: new Date(h.date || h.scanned_at).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    score: h.score,
  }));

  const grade =
    data.length > 0 && data[data.length - 1].score >= 90
      ? 'A'
      : data.length > 0 && data[data.length - 1].score >= 80
      ? 'B'
      : data.length > 0 && data[data.length - 1].score >= 70
      ? 'C'
      : data.length > 0 && data[data.length - 1].score >= 60
      ? 'D'
      : 'F';

  const lineColor = GRADE_COLORS[grade] || '#FF6B35';

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1f2937' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1f2937' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="score"
            stroke={lineColor}
            strokeWidth={2}
            dot={{ fill: lineColor, r: 3 }}
            activeDot={{ r: 5 }}
            isAnimationActive
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}