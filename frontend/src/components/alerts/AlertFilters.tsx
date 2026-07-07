import { Search, X } from "lucide-react";
import { useCategories } from "../../hooks/useCategories";
import { useSources } from "../../hooks/useSources";

interface Props {
  severity: string;
  source: string;
  search: string;
  category: string;
  dateFrom: string;
  dateTo: string;
  showAcknowledged: boolean;
  onSeverity: (v: string) => void;
  onSource: (v: string) => void;
  onSearch: (v: string) => void;
  onCategory: (v: string) => void;
  onDateFrom: (v: string) => void;
  onDateTo: (v: string) => void;
  onShowAcknowledged: (v: boolean) => void;
}

const SEVERITIES = ["", "critical", "high", "medium", "low", "info"];

export default function AlertFilters({
  severity,
  source,
  search,
  category,
  dateFrom,
  dateTo,
  showAcknowledged,
  onSeverity,
  onSource,
  onSearch,
  onCategory,
  onDateFrom,
  onDateTo,
  onShowAcknowledged,
}: Props) {
  const { data: categories = [] } = useCategories();
  const { data: sourcesData = [] } = useSources();

  const selectClass =
    "bg-[#1f2937] border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-blue-500";
  const inputClass =
    "bg-[#1f2937] border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-blue-500";

  const hasDateFilter = dateFrom || dateTo;

  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="relative flex-1 min-w-48">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search alerts..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="w-full bg-[#1f2937] border border-gray-700 text-gray-200 text-sm rounded-md pl-9 pr-3 py-1.5 focus:outline-none focus:border-blue-500"
        />
      </div>

      <select
        value={severity}
        onChange={(e) => onSeverity(e.target.value)}
        className={selectClass}
      >
        <option value="">All severities</option>
        {SEVERITIES.filter(Boolean).map((s) => (
          <option key={s} value={s}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </option>
        ))}
      </select>

      <select
        value={source}
        onChange={(e) => onSource(e.target.value)}
        className={selectClass}
      >
        <option value="">All sources</option>
        {sourcesData.map((s) => (
          <option key={s.id} value={s.name}>
            {s.name}
          </option>
        ))}
      </select>

      {categories.length > 0 && (
        <select
          value={category}
          onChange={(e) => onCategory(e.target.value)}
          className={selectClass}
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.name}>
              {c.name.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      )}

      <input
        type="date"
        value={dateFrom}
        onChange={(e) => onDateFrom(e.target.value)}
        title="From date"
        className={inputClass}
      />
      <input
        type="date"
        value={dateTo}
        onChange={(e) => onDateTo(e.target.value)}
        title="To date"
        className={inputClass}
      />

      {hasDateFilter && (
        <button
          onClick={() => { onDateFrom(""); onDateTo(""); }}
          className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-400 hover:text-gray-200 border border-gray-700 rounded-md"
          title="Clear date filter"
        >
          <X className="h-3 w-3" />
          Clear dates
        </button>
      )}

      <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-400 hover:text-gray-200 transition-colors">
        <input
          type="checkbox"
          checked={showAcknowledged}
          onChange={(e) => onShowAcknowledged(e.target.checked)}
          className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900"
        />
        Show acknowledged
      </label>
    </div>
  );
}
