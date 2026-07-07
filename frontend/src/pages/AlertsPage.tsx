import { useSearchParams } from "react-router-dom";
import { Download } from "lucide-react";
import type { AlertSortField } from "../types/alert";
import { useAlerts } from "../hooks/useAlerts";
import { alertsApi } from "../services/alerts";
import Header from "../components/layout/Header";
import AlertFilters from "../components/alerts/AlertFilters";
import AlertTable from "../components/alerts/AlertTable";
import Pagination from "../components/common/Pagination";
import ErrorMessage from "../components/common/ErrorMessage";

export default function AlertsPage() {
  const [params, setParams] = useSearchParams();

  const page = parseInt(params.get("page") ?? "1", 10);
  const severity = params.get("severity") ?? "";
  const source = params.get("source") ?? "";
  const search = params.get("search") ?? "";
  const category = params.get("category") ?? "";
  const dateFrom = params.get("date_from") ?? "";
  const dateTo = params.get("date_to") ?? "";
  const sortBy = (params.get("sort_by") ?? "normalized_at") as AlertSortField;
  const sortOrder = (params.get("sort_order") ?? "desc") as "asc" | "desc";
  const showAcknowledged = params.get("acknowledged") === "true";

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.set("page", "1");
    setParams(next);
  };

  const handleSort = (field: AlertSortField) => {
    const next = new URLSearchParams(params);
    if (field === sortBy) {
      next.set("sort_order", sortOrder === "asc" ? "desc" : "asc");
    } else {
      next.set("sort_by", field);
      next.set("sort_order", "desc");
    }
    next.set("page", "1");
    setParams(next);
  };

  const { data, isLoading, error, refetch } = useAlerts({
    page,
    page_size: 20,
    severity: severity || undefined,
    source: source || undefined,
    search: search || undefined,
    category: category || undefined,
    date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
    date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    is_acknowledged: showAcknowledged ? undefined : false,
  });

  const handleExportCsv = () => {
    const p: Record<string, string> = {};
    if (severity) p.severity = severity;
    if (source) p.source = source;
    if (search) p.search = search;
    if (category) p.category = category;
    if (dateFrom) p.date_from = `${dateFrom}T00:00:00Z`;
    if (dateTo) p.date_to = `${dateTo}T23:59:59Z`;
    alertsApi.exportCsv(p);
  };

  return (
    <div>
      <Header
        title="Alerts"
        subtitle={data ? `${data.total.toLocaleString()} total alerts` : undefined}
        actions={
          <button
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white border border-gray-700 transition-colors"
            title="Export current filter as CSV"
          >
            <Download className="h-3.5 w-3.5" />
            Export CSV
          </button>
        }
      />

      <AlertFilters
        severity={severity}
        source={source}
        search={search}
        category={category}
        dateFrom={dateFrom}
        dateTo={dateTo}
        showAcknowledged={showAcknowledged}
        onSeverity={(v) => setParam("severity", v)}
        onSource={(v) => setParam("source", v)}
        onSearch={(v) => setParam("search", v)}
        onCategory={(v) => setParam("category", v)}
        onDateFrom={(v) => setParam("date_from", v)}
        onDateTo={(v) => setParam("date_to", v)}
        onShowAcknowledged={(v) => setParam("acknowledged", v ? "true" : "")}
      />

      {error && !isLoading && <ErrorMessage onRetry={refetch} />}

      <div className="bg-[#111827] border border-gray-800 rounded-lg">
        <AlertTable
          alerts={data?.items ?? []}
          isLoading={isLoading}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={handleSort}
        />
        {data && (
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(p) => {
              const next = new URLSearchParams(params);
              next.set("page", String(p));
              setParams(next);
            }}
          />
        )}
      </div>
    </div>
  );
}
