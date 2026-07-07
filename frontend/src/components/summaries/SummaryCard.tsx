import { Link } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import type { Summary } from "../../types/summary";
import { formatDateTime } from "../../lib/formatters";

interface Props {
  summary: Summary;
}

export default function SummaryCard({ summary }: Props) {
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <MessageSquare className="h-4 w-4 text-gray-500 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className={`text-xs px-2 py-0.5 rounded border capitalize ${
                summary.summary_type === "digest"
                  ? "text-blue-400 bg-blue-500/10 border-blue-500/20"
                  : "text-gray-400 bg-gray-500/10 border-gray-500/20"
              }`}
            >
              {summary.summary_type}
            </span>
            <span className="text-xs text-gray-500">
              {formatDateTime(summary.created_at)}
            </span>
            {summary.normalized_alert_id && (
              <Link
                to={`/alerts/${summary.normalized_alert_id}`}
                className="text-xs text-blue-400 hover:underline"
              >
                Alert #{summary.normalized_alert_id}
              </Link>
            )}
          </div>
          <p className="text-sm text-gray-300 line-clamp-3 leading-relaxed">
            {summary.content}
          </p>
          <p className="text-xs text-gray-600 mt-1.5">{summary.model_used}</p>
        </div>
      </div>
    </div>
  );
}
