import { useParams, Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { useAlert } from "../hooks/useAlerts";
import { useSummaries } from "../hooks/useSummaries";
import AlertDetailCard from "../components/alerts/AlertDetailCard";
import SummaryCard from "../components/summaries/SummaryCard";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";

export default function AlertDetailPage() {
  const { id } = useParams<{ id: string }>();
  const alertId = parseInt(id ?? "0", 10);

  const { data: alert, isLoading, error, refetch } = useAlert(alertId);

  // Fetch summary for this specific alert
  const { data: summaryList } = useSummaries({
    normalized_alert_id: alertId,
    page_size: 1,
  });

  const alertSummary = summaryList?.items[0];

  if (isLoading) return <LoadingSpinner text="Loading alert..." />;
  if (error || !alert) return <ErrorMessage onRetry={refetch} />;

  return (
    <div>
      <Link
        to="/alerts"
        className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white mb-5 transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to Alerts
      </Link>

      <AlertDetailCard alert={alert} />

      {alertSummary && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">AI Summary</h3>
          <SummaryCard summary={alertSummary} />
        </div>
      )}
    </div>
  );
}
