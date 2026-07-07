import { Link } from "react-router-dom";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import type { Alert, AlertSortField } from "../../types/alert";
import SeverityBadge from "../common/SeverityBadge";
import { formatDate, formatCVSS } from "../../lib/formatters";
import EmptyState from "../common/EmptyState";
import SkeletonRows from "../common/SkeletonRows";

interface Props {
  alerts: Alert[];
  isLoading?: boolean;
  sortBy?: AlertSortField;
  sortOrder?: "asc" | "desc";
  onSort?: (field: AlertSortField) => void;
}

const COLS = 5;

function SortIcon({ field, sortBy, sortOrder }: { field: AlertSortField; sortBy?: AlertSortField; sortOrder?: "asc" | "desc" }) {
  if (field !== sortBy) return <ChevronsUpDown className="h-3 w-3 ml-1 opacity-30" />;
  return sortOrder === "asc"
    ? <ChevronUp className="h-3 w-3 ml-1 text-blue-400" />
    : <ChevronDown className="h-3 w-3 ml-1 text-blue-400" />;
}

export default function AlertTable({ alerts, isLoading, sortBy, sortOrder, onSort }: Props) {
  const th = (label: string, field: AlertSortField) => (
    <th
      className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-300 transition-colors"
      onClick={() => onSort?.(field)}
    >
      <span className="flex items-center">
        {label}
        <SortIcon field={field} sortBy={sortBy} sortOrder={sortOrder} />
      </span>
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left">
            {th("Severity", "severity")}
            {th("Title", "title")}
            {th("Source", "source_name")}
            {th("CVSS", "cvss_score")}
            {th("Published", "published_date")}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {isLoading && <SkeletonRows rows={8} cols={COLS} />}
          {!isLoading && alerts.length === 0 && (
            <tr>
              <td colSpan={COLS}>
                <EmptyState message="No alerts match your filters" />
              </td>
            </tr>
          )}
          {!isLoading && alerts.map((alert) => (
            <tr
              key={alert.id}
              className={`hover:bg-gray-800/40 transition-colors ${alert.is_acknowledged ? "opacity-50" : ""}`}
            >
              <td className="px-4 py-3">
                <SeverityBadge severity={alert.severity} />
              </td>
              <td className="px-4 py-3 max-w-md">
                <Link
                  to={`/alerts/${alert.id}`}
                  className="text-gray-200 hover:text-blue-400 transition-colors font-medium truncate block"
                >
                  {alert.is_acknowledged && (
                    <span className="text-[10px] bg-gray-700 text-gray-400 rounded px-1 mr-1.5">ACK</span>
                  )}
                  {alert.title}
                </Link>
                {alert.description && (
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {alert.description}
                  </p>
                )}
              </td>
              <td className="px-4 py-3">
                <span className="text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                  {alert.source_name}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-300">
                {formatCVSS(alert.cvss_score)}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {formatDate(alert.published_date ?? alert.normalized_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
