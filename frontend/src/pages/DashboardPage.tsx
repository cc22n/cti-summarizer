import { useDashboardOverview, useTimeline } from "../hooks/useDashboard";
import { useAlerts, useAlertStats } from "../hooks/useAlerts";
import Header from "../components/layout/Header";
import OverviewCards from "../components/dashboard/OverviewCards";
import TimelineChart from "../components/dashboard/TimelineChart";
import SeverityPieChart from "../components/dashboard/SeverityPieChart";
import SourceBarChart from "../components/dashboard/SourceBarChart";
import RecentAlertsTable from "../components/dashboard/RecentAlertsTable";
import ErrorMessage from "../components/common/ErrorMessage";
import { SkeletonCard } from "../components/common/SkeletonRows";
import {
  transformTimeline,
  transformSeverityPie,
  transformSourceBar,
} from "../lib/chartUtils";

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { data: overview, isLoading: ovLoading, error: ovError, refetch: refetchOv } = useDashboardOverview();
  const { data: timeline } = useTimeline(30);
  const { data: stats } = useAlertStats();
  const { data: recentAlerts } = useAlerts({ page: 1, page_size: 10 });

  if (ovLoading) {
    return (
      <div>
        <Header title="Dashboard" subtitle="Threat intelligence overview" />
        <OverviewSkeleton />
        <div className="bg-[#111827] border border-gray-800 rounded-lg h-72 animate-pulse mb-4" />
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
          <div className="bg-[#111827] border border-gray-800 rounded-lg h-48 animate-pulse" />
          <div className="xl:col-span-2 bg-[#111827] border border-gray-800 rounded-lg h-48 animate-pulse" />
        </div>
      </div>
    );
  }
  if (ovError || !overview) return <ErrorMessage onRetry={refetchOv} />;

  const timelineData = timeline ? transformTimeline(timeline.points) : [];
  const pieData = stats ? transformSeverityPie(stats.by_severity) : [];
  const barData = stats ? transformSourceBar(stats.by_source) : [];

  return (
    <div>
      <Header
        title="Dashboard"
        subtitle="Threat intelligence overview"
      />

      <OverviewCards data={overview} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
        <div className="xl:col-span-3">
          <TimelineChart data={timelineData} />
        </div>
        <SeverityPieChart data={pieData} />
        <div className="xl:col-span-2">
          <SourceBarChart data={barData} />
        </div>
      </div>

      <RecentAlertsTable alerts={recentAlerts?.items ?? []} />
    </div>
  );
}
