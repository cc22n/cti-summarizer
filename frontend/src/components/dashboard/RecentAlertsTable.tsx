import { Link } from "react-router-dom";
import type { Alert } from "../../types/alert";
import SeverityBadge from "../common/SeverityBadge";
import { formatRelativeTime } from "../../lib/formatters";

interface Props {
  alerts: Alert[];
}

export default function RecentAlertsTable({ alerts }: Props) {
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg">
      <div className="px-4 py-3 border-b border-gray-800">
        <h3 className="text-sm font-medium text-gray-300">Recent Alerts</h3>
      </div>
      <div className="divide-y divide-gray-800">
        {alerts.slice(0, 10).map((alert) => (
          <Link
            key={alert.id}
            to={`/alerts/${alert.id}`}
            className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800/50 transition-colors"
          >
            <SeverityBadge severity={alert.severity} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-200 truncate">{alert.title}</p>
              <p className="text-xs text-gray-500">{alert.source_name}</p>
            </div>
            <span className="text-xs text-gray-600 shrink-0">
              {formatRelativeTime(alert.normalized_at)}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
