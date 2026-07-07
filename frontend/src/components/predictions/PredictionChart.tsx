import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import type { PredictionPoint } from "../../types/prediction";
import type { TimelinePoint } from "../../types/dashboard";
import { SEVERITY_COLORS } from "../../lib/chartUtils";

type SeriesKey = "critical" | "high" | "medium" | "low";

interface MergedPoint {
  date: string;
  actual_critical?: number;
  actual_high?: number;
  actual_medium?: number;
  actual_low?: number;
  pred_critical?: number;
  pred_high?: number;
  pred_medium?: number;
  pred_low?: number;
  pred_total?: number;
  total_lower?: number;
  total_upper?: number;
}

interface Props {
  history: TimelinePoint[];
  predictions: Record<string, PredictionPoint[]>;
  visibleSeries: string[];
}

const SERIES: SeriesKey[] = ["critical", "high", "medium", "low"];

export default function PredictionChart({
  history,
  predictions,
  visibleSeries,
}: Props) {
  const pointMap = new Map<string, MergedPoint>();

  for (const h of history) {
    pointMap.set(h.date, {
      date: h.date,
      actual_critical: h.severity_breakdown?.critical ?? 0,
      actual_high: h.severity_breakdown?.high ?? 0,
      actual_medium: h.severity_breakdown?.medium ?? 0,
      actual_low: h.severity_breakdown?.low ?? 0,
    });
  }

  for (const [key, points] of Object.entries(predictions)) {
    for (const p of points) {
      const existing: MergedPoint = pointMap.get(p.date) ?? { date: p.date };
      if (key === "total") {
        existing.pred_total = p.predicted;
        existing.total_lower = p.lower;
        existing.total_upper = p.upper;
      } else {
        (existing as unknown as Record<string, unknown>)[`pred_${key}`] = p.predicted;
      }
      pointMap.set(p.date, existing);
    }
  }

  const data = Array.from(pointMap.values()).sort((a, b) =>
    a.date.localeCompare(b.date)
  );
  const today = new Date().toISOString().slice(0, 10);

  const anomalyCount = Object.values(predictions)
    .flat()
    .filter((p) => p.is_anomaly).length;

  const anomalyDates = new Set(
    Object.values(predictions)
      .flat()
      .filter((p) => p.is_anomaly)
      .map((p) => p.date)
  );

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300">
          30d Actual + 14d Forecast
        </h3>
        {anomalyCount > 0 && (
          <span className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded px-2 py-0.5">
            {anomalyCount} anomalous point{anomalyCount !== 1 ? "s" : ""} detected
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart
          data={data}
          margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1f2937"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => d.slice(5)}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "#1f2937",
              border: "1px solid #374151",
              borderRadius: 6,
              fontSize: 12,
            }}
            labelStyle={{ color: "#d1d5db" }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(v) => (
              <span style={{ color: "#9ca3af" }}>{v}</span>
            )}
          />
          <ReferenceLine
            x={today}
            stroke="#4b5563"
            strokeDasharray="4 4"
            label={{
              value: "Today",
              position: "insideTopRight",
              fill: "#6b7280",
              fontSize: 10,
            }}
          />

          {/* Amber background highlight for anomalous forecast dates */}
          {Array.from(anomalyDates).map((d) => (
            <ReferenceArea
              key={`anom_${d}`}
              x1={d}
              x2={d}
              fill="#fbbf24"
              fillOpacity={0.12}
              stroke="#fbbf24"
              strokeOpacity={0.25}
              strokeWidth={1}
            />
          ))}

          {/* Confidence band for total series */}
          {visibleSeries.includes("total") && (
            <Area
              dataKey="total_upper"
              fill="#3b82f6"
              fillOpacity={0.07}
              stroke="none"
              legendType="none"
              name=""
            />
          )}

          {/* Actual historical lines */}
          {SERIES.filter((s) => visibleSeries.includes(s)).map((s) => (
            <Line
              key={`actual_${s}`}
              type="monotone"
              dataKey={`actual_${s}`}
              stroke={SEVERITY_COLORS[s]}
              strokeWidth={1.5}
              dot={false}
              name={s}
              connectNulls={false}
            />
          ))}

          {/* Predicted dashed lines */}
          {SERIES.filter((s) => visibleSeries.includes(s)).map((s) => (
            <Line
              key={`pred_${s}`}
              type="monotone"
              dataKey={`pred_${s}`}
              stroke={SEVERITY_COLORS[s]}
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              legendType="none"
              name={`${s} (predicted)`}
              connectNulls={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
