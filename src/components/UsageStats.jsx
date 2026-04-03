import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";

// Base URL for the backend API
const API_BASE = "http://127.0.0.1:8000";

// Number of days to request from the stats endpoint
const STATS_DAYS = 7;

/**
 * Demo auth token — the backend currently accepts a raw user ID as the Bearer token.
 * Replace this with a real JWT retrieved from your auth flow in production.
 */
const AUTH_TOKEN = "1";

/**
 * UsageStats
 *
 * Fetches usage analytics from GET /api/usage/stats and renders:
 * - A progress bar showing today's committed turns vs. the daily limit
 * - A bar chart of daily committed usage over the requested period
 * - A summary grid: total, average, peak day, and current streak
 *
 * Handles loading and error states explicitly.
 */
const UsageStats = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${API_BASE}/api/usage/stats?days=${STATS_DAYS}`, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      })
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <p style={styles.status}>Loading...</p>;
  if (error) return <p style={styles.status}>Error: {error}</p>;

  // The last entry in the days array always represents today
  const today = data.days[data.days.length - 1];

  // Cap at 100% so the bar does not overflow when the limit is exceeded
  const todayPct = Math.min((today.committed / data.daily_limit) * 100, 100);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Fidant Usage Dashboard</h2>
      <p style={styles.sub}>
        Plan: <strong>{data.plan}</strong> · Daily limit:{" "}
        <strong>{data.daily_limit}</strong>
      </p>
      <p style={styles.sub}>
        Period: {data.period.from} to {data.period.to}
      </p>

      {/* Today's progress bar */}
      <div style={styles.section}>
        <p style={styles.label}>
          Today: {today.committed} / {data.daily_limit} committed
        </p>
        <div
          style={styles.progressTrack}
          role="progressbar"
          aria-valuenow={today.committed}
          aria-valuemax={data.daily_limit}
        >
          <div style={{ ...styles.progressFill, width: `${todayPct}%` }} />
        </div>
        <p style={styles.hint}>{today.reserved} active reservation(s)</p>
      </div>

      {/* Daily usage bar chart — bars turn red when the daily limit is reached */}
      <div style={styles.section}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={data.days}
            margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
          >
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            {/* Dashed reference line marks the daily limit */}
            <ReferenceLine
              y={data.daily_limit}
              stroke="#ef4444"
              strokeDasharray="4 2"
              label={{ value: "limit", fontSize: 11 }}
            />
            <Bar dataKey="committed" name="Committed" radius={[4, 4, 0, 0]}>
              {data.days.map((d) => (
                // Use date as the key — it is unique within the period
                <Cell
                  key={d.date}
                  fill={d.utilization >= 1 ? "#ef4444" : "#6366f1"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Summary statistics grid */}
      <div style={styles.grid}>
        <Stat label="Total committed" value={data.summary.total_committed} />
        <Stat label="Avg daily" value={data.summary.avg_daily} />
        <Stat
          label="Peak day"
          value={`${data.summary.peak_day.date} (${data.summary.peak_day.count})`}
        />
        <Stat
          label="Current streak"
          value={`${data.summary.current_streak} day(s)`}
        />
      </div>
    </div>
  );
};

/**
 * Stat
 *
 * A single labelled metric card used in the summary grid.
 */
const Stat = ({ label, value }) => (
  <div style={styles.statBox}>
    <p style={styles.statLabel}>{label}</p>
    <p style={styles.statValue}>{value}</p>
  </div>
);

const styles = {
  container: {
    maxWidth: 720,
    margin: "0 auto",
    fontFamily: "system-ui, sans-serif",
    padding: 24,
  },
  title: { fontSize: 22, marginBottom: 4 },
  sub: { color: "#6b7280", fontSize: 14, margin: "2px 0" },
  section: { margin: "20px 0" },
  label: { fontSize: 14, marginBottom: 6 },
  progressTrack: {
    height: 12,
    background: "#e5e7eb",
    borderRadius: 6,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    background: "#6366f1",
    borderRadius: 6,
    transition: "width 0.4s",
  },
  hint: { fontSize: 12, color: "#9ca3af", marginTop: 4 },
  grid: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 },
  statBox: { background: "#f9fafb", borderRadius: 8, padding: "12px 16px" },
  statLabel: { fontSize: 12, color: "#6b7280", margin: 0 },
  statValue: { fontSize: 18, fontWeight: 600, margin: "4px 0 0" },
  status: { padding: 24, color: "#6b7280" },
};

export default UsageStats;
