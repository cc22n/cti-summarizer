import { Link } from "react-router-dom";
import { ShieldAlert, TrendingUp, Activity, Zap, Server, Clock } from "lucide-react";
import type { DashboardOverview } from "../../types/dashboard";
import { formatRelativeTime } from "../../lib/formatters";

interface Props {
  data: DashboardOverview;
}

export default function OverviewCards({ data }: Props) {
  const cards: Array<{
    label: string;
    value: string;
    icon: typeof ShieldAlert;
    color: string;
    bg: string;
    sub?: string;
    to?: string;
  }> = [
    {
      label: "Total Alerts",
      value: data.total_alerts.toLocaleString(),
      icon: ShieldAlert,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      to: "/alerts",
    },
    {
      label: "Last 24h",
      value: data.alerts_today.toLocaleString(),
      icon: Clock,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
    },
    {
      label: "This Week",
      value: data.alerts_this_week.toLocaleString(),
      icon: TrendingUp,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
    },
    {
      label: "Critical",
      value: data.critical_count.toLocaleString(),
      icon: Zap,
      color: "text-red-400",
      bg: "bg-red-500/10",
      to: "/alerts?severity=critical",
    },
    {
      label: "High",
      value: data.high_count.toLocaleString(),
      icon: Activity,
      color: "text-orange-400",
      bg: "bg-orange-500/10",
      to: "/alerts?severity=high",
    },
    {
      label: "Sources",
      value: `${data.sources_active} / ${data.sources_total}`,
      icon: Server,
      color: "text-green-400",
      bg: "bg-green-500/10",
      sub: data.last_ingestion
        ? `Last: ${formatRelativeTime(data.last_ingestion)}`
        : undefined,
      to: "/sources",
    },
  ];

  const cardClass =
    "bg-[#111827] border border-gray-800 rounded-lg p-4 flex flex-col gap-3";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
      {cards.map(({ label, value, icon: Icon, color, bg, sub, to }) => {
        const inner = (
          <>
            <div className={`w-8 h-8 rounded-md ${bg} flex items-center justify-center`}>
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-white leading-none">{value}</p>
              <p className="text-xs text-gray-400 mt-1">{label}</p>
              {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
            </div>
          </>
        );
        return to ? (
          <Link
            key={label}
            to={to}
            className={`${cardClass} hover:border-gray-600 transition-colors`}
          >
            {inner}
          </Link>
        ) : (
          <div key={label} className={cardClass}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}
