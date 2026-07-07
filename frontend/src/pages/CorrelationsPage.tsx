import { useState } from "react";
import { Link } from "react-router-dom";
import { GitMerge, ExternalLink } from "lucide-react";
import { useCorrelations } from "../hooks/useAlerts";
import Header from "../components/layout/Header";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import SeverityBadge from "../components/common/SeverityBadge";
import type { CorrelationGroup, Severity } from "../types/alert";

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

function topSeverity(severities: string[]): Severity {
  const sorted = [...severities].sort(
    (a, b) => (SEVERITY_ORDER[a] ?? 9) - (SEVERITY_ORDER[b] ?? 9)
  );
  return (sorted[0] ?? "info") as Severity;
}

export default function CorrelationsPage() {
  const [minCount, setMinCount] = useState(2);
  const { data, isLoading, error, refetch } = useCorrelations(minCount);

  const groups = data?.groups ?? [];
  const cveGroups = groups.filter((g) => g.group_type === "cve");
  const vendorGroups = groups.filter((g) => g.group_type === "vendor");

  return (
    <div>
      <Header
        title="Correlations"
        subtitle="Alerts grouped by shared CVE ID or vendor"
      />

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-400">
          Min alerts per group:
        </label>
        {[2, 3, 5].map((n) => (
          <button
            key={n}
            onClick={() => setMinCount(n)}
            className={`px-3 py-1 rounded text-xs font-medium border transition-colors ${
              minCount === n
                ? "bg-blue-600/20 border-blue-500 text-blue-400"
                : "border-gray-700 text-gray-500 hover:text-gray-300"
            }`}
          >
            {n}+
          </button>
        ))}
        <span className="text-xs text-gray-500 ml-2">
          {groups.length} group{groups.length !== 1 ? "s" : ""}
        </span>
      </div>

      {isLoading && <LoadingSpinner text="Analyzing correlations..." />}
      {error && <ErrorMessage onRetry={refetch} />}

      {!isLoading && groups.length === 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-lg p-10 text-center">
          <GitMerge className="h-8 w-8 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">
            No correlation groups found with {minCount}+ alerts.
          </p>
          <p className="text-gray-600 text-xs mt-1">
            Try lowering the minimum count, or wait for more data to be ingested.
          </p>
        </div>
      )}

      {cveGroups.length > 0 && (
        <Section title="CVE Correlations" groups={cveGroups} />
      )}
      {vendorGroups.length > 0 && (
        <Section title="Vendor Correlations" groups={vendorGroups} />
      )}
    </div>
  );
}

function Section({
  title,
  groups,
}: {
  title: string;
  groups: CorrelationGroup[];
}) {
  return (
    <div className="mb-6">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
        {title}
      </h2>
      <div className="bg-[#111827] border border-gray-800 rounded-lg divide-y divide-gray-800">
        {groups.map((g) => (
          <div key={`${g.group_type}-${g.key}`} className="px-4 py-3 flex items-start gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={topSeverity(g.severities)} />
                <span className="text-sm font-medium text-white truncate">{g.key}</span>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                <span>{g.count} alert{g.count !== 1 ? "s" : ""}</span>
                <span>Sources: {g.sources.join(", ")}</span>
                <span>Severities: {g.severities.join(", ")}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-1 shrink-0 max-w-xs">
              {g.alert_ids.slice(0, 8).map((id) => (
                <Link
                  key={id}
                  to={`/alerts/${id}`}
                  className="text-[10px] bg-gray-800 text-blue-400 hover:text-blue-300 rounded px-1.5 py-0.5 flex items-center gap-0.5 transition-colors"
                >
                  #{id}
                  <ExternalLink className="h-2.5 w-2.5" />
                </Link>
              ))}
              {g.alert_ids.length > 8 && (
                <span className="text-[10px] text-gray-600 px-1.5 py-0.5">
                  +{g.alert_ids.length - 8} more
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
