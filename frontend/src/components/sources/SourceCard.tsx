import { RefreshCw, CheckCircle, XCircle, Clock, Power } from "lucide-react";
import type { Source } from "../../types/source";
import { useSourceHealth, usePollSource, useToggleSource } from "../../hooks/useSources";
import { formatRelativeTime } from "../../lib/formatters";

interface Props {
  source: Source;
}

export default function SourceCard({ source }: Props) {
  const { data: health } = useSourceHealth(source.id);
  const { mutate: poll, isPending } = usePollSource();
  const { mutate: toggle, isPending: isToggling } = useToggleSource();

  const status = health?.last_status ?? "unknown";
  const isError = status === "error";
  const isSuccess = status === "success";

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-white text-sm">{source.name}</span>
            {isSuccess && <CheckCircle className="h-3.5 w-3.5 text-green-400" />}
            {isError && <XCircle className="h-3.5 w-3.5 text-red-400" />}
          </div>
          <span className="text-xs text-gray-500 capitalize">{source.source_type}</span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded border ${
            source.is_active
              ? "text-green-400 bg-green-500/10 border-green-500/20"
              : "text-gray-500 bg-gray-500/10 border-gray-500/20"
          }`}
        >
          {source.is_active ? "active" : "inactive"}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-gray-900 rounded p-2">
          <p className="text-gray-500 mb-0.5">Last polled</p>
          <p className="text-gray-300">
            {formatRelativeTime(health?.last_polled_at ?? source.last_polled_at)}
          </p>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <p className="text-gray-500 mb-0.5">Alerts (24h)</p>
          <p className="text-gray-300">{health?.alerts_last_24h ?? 0}</p>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <p className="text-gray-500 mb-0.5">Poll interval</p>
          <p className="text-gray-300">
            {source.polling_interval_minutes >= 1440
              ? `${source.polling_interval_minutes / 1440}d`
              : `${source.polling_interval_minutes / 60}h`}
          </p>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <p className="text-gray-500 mb-0.5">Errors (24h)</p>
          <p
            className={
              (health?.error_count_last_24h ?? 0) > 0
                ? "text-red-400"
                : "text-gray-300"
            }
          >
            {health?.error_count_last_24h ?? 0}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => poll(source.id)}
          disabled={isPending || !source.is_active}
          className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-xs font-medium bg-blue-600/10 text-blue-400 border border-blue-600/20 hover:bg-blue-600/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isPending ? "animate-spin" : ""}`} />
          {isPending ? "Triggering..." : "Poll now"}
        </button>
        <button
          onClick={() => toggle(source.id)}
          disabled={isToggling}
          title={source.is_active ? "Disable source" : "Enable source"}
          className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            source.is_active
              ? "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20"
              : "bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/20"
          }`}
        >
          <Power className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Last status */}
      {health?.last_status && (
        <div className="flex items-start gap-1.5">
          <Clock className="h-3 w-3 text-gray-600 mt-0.5 shrink-0" />
          <div>
            <span className="text-xs text-gray-600">
              Last run: {health.last_status}
            </span>
            {health.last_status === "error" && health.last_error_message && (
              <p className="text-xs text-red-400 mt-0.5 leading-snug">
                {health.last_error_message.slice(0, 120)}
                {health.last_error_message.length > 120 ? "…" : ""}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
