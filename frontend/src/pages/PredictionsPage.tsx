import { useState } from "react";
import { Zap, Loader2 } from "lucide-react";
import { useLatestPredictions, useGeneratePredictions } from "../hooks/usePredictions";
import { useTimeline } from "../hooks/useDashboard";
import Header from "../components/layout/Header";
import PredictionChart from "../components/predictions/PredictionChart";
import LoadingSpinner from "../components/common/LoadingSpinner";
import { formatDateTime } from "../lib/formatters";
import { SEVERITY_COLORS } from "../lib/chartUtils";

const ALL_SERIES = ["critical", "high", "medium", "low"] as const;

export default function PredictionsPage() {
  const [visibleSeries, setVisibleSeries] = useState<string[]>([...ALL_SERIES]);

  const {
    data: predictions,
    isLoading,
    error,
  } = useLatestPredictions();
  const { data: timeline } = useTimeline(30);
  const { mutate: generate, isPending, isSuccess: genSuccess } = useGeneratePredictions();

  const toggleSeries = (s: string) => {
    setVisibleSeries((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  return (
    <div>
      <Header
        title="Predictions"
        subtitle="Prophet time series forecast — 14-day threat volume outlook"
      />

      {/* Controls */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex gap-2 flex-wrap">
          {ALL_SERIES.map((s) => (
            <button
              key={s}
              onClick={() => toggleSeries(s)}
              className="px-3 py-1 rounded text-xs font-medium border transition-colors"
              style={
                visibleSeries.includes(s)
                  ? {
                      backgroundColor: SEVERITY_COLORS[s] + "22",
                      borderColor: SEVERITY_COLORS[s],
                      color: SEVERITY_COLORS[s],
                    }
                  : {
                      backgroundColor: "transparent",
                      borderColor: "#374151",
                      color: "#6b7280",
                    }
              }
            >
              {s}
            </button>
          ))}
        </div>

        <button
          onClick={() => generate()}
          disabled={isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Zap className="h-3.5 w-3.5" />
          )}
          Regenerate
        </button>
      </div>

      {/* Meta info */}
      {predictions && (
        <p className="text-xs text-gray-500 mb-3">
          Generated: {formatDateTime(predictions.generated_at)}
          &nbsp;&middot;&nbsp;
          Trained on {predictions.training_days} days
          &nbsp;&middot;&nbsp;
          Model: {predictions.model_type}
        </p>
      )}

      {genSuccess && (
        <p className="text-xs text-green-400 mb-3">
          Prediction run queued. Results will appear shortly.
        </p>
      )}

      {/* Chart */}
      {isLoading && <LoadingSpinner text="Loading predictions..." />}

      {error && !predictions && (
        <div className="bg-[#111827] border border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-400 text-sm mb-3">
            No predictions available yet.
          </p>
          <p className="text-gray-600 text-xs">
            Click "Regenerate" to generate the first forecast.
          </p>
        </div>
      )}

      {predictions && timeline && (
        <PredictionChart
          history={timeline.points}
          predictions={predictions.series}
          visibleSeries={visibleSeries}
        />
      )}

      {/* Forecast table */}
      {predictions && (
        <div className="mt-4 bg-[#111827] border border-gray-800 rounded-lg">
          <div className="px-4 py-3 border-b border-gray-800">
            <h3 className="text-sm font-medium text-gray-300">
              14-Day Forecast
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-2 text-gray-500">Date</th>
                  {ALL_SERIES.map((s) => (
                    <th
                      key={s}
                      className="text-right px-4 py-2 text-gray-500 capitalize"
                    >
                      {s}
                    </th>
                  ))}
                  <th className="text-right px-4 py-2 text-gray-500">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {(() => {
                  // Build a date-keyed map across all series so the table
                  // is resilient to series with different point counts.
                  const dateMap = new Map<string, Record<string, import("../types/prediction").PredictionPoint>>();
                  for (const [key, pts] of Object.entries(predictions.series)) {
                    for (const pt of pts) {
                      if (!dateMap.has(pt.date)) dateMap.set(pt.date, {});
                      dateMap.get(pt.date)![key] = pt;
                    }
                  }
                  return Array.from(dateMap.keys())
                    .sort()
                    .map((d) => {
                      const row = dateMap.get(d)!;
                      const hasAnomaly = Object.values(row).some((p) => p.is_anomaly);
                      return (
                        <tr
                          key={d}
                          className={`hover:bg-gray-800/40 ${hasAnomaly ? "bg-amber-950/30" : ""}`}
                        >
                          <td className={`px-4 py-2 flex items-center gap-1 ${hasAnomaly ? "text-amber-400 font-medium" : "text-gray-400"}`}>
                            {d}
                            {hasAnomaly && (
                              <span className="text-amber-400 text-[10px] ml-0.5" title="Anomaly detected">&#9888;</span>
                            )}
                          </td>
                          {ALL_SERIES.map((s) => {
                            const pt = row[s];
                            return (
                              <td
                                key={s}
                                className={`px-4 py-2 text-right ${pt?.is_anomaly ? "text-amber-400 font-medium" : "text-gray-300"}`}
                              >
                                {pt?.predicted ?? "—"}
                              </td>
                            );
                          })}
                          <td className="px-4 py-2 text-right text-gray-300">
                            {row["total"]?.predicted ?? "—"}
                          </td>
                        </tr>
                      );
                    });
                })()}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
