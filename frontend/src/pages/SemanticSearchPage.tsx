import { useState } from "react";
import { Search, Cpu } from "lucide-react";
import { Link } from "react-router-dom";
import { useSemanticSearch } from "../hooks/useAlerts";
import Header from "../components/layout/Header";
import SeverityBadge from "../components/common/SeverityBadge";
import { formatDateTime } from "../lib/formatters";

export default function SemanticSearchPage() {
  const [query, setQuery] = useState("");

  const { data, isLoading, isFetching, isError } = useSemanticSearch(query, 20);
  const results = data?.results ?? [];
  const method = data?.method;

  return (
    <div>
      <Header
        title="Semantic Search"
        subtitle="Natural language search over threat intelligence"
      />

      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. ransomware lateral movement, Apache RCE, credential theft..."
          className="w-full bg-[#111827] border border-gray-700 text-gray-200 rounded-lg pl-12 pr-4 py-3 text-sm focus:outline-none focus:border-blue-500 placeholder-gray-600"
          autoFocus
        />
        {(isLoading || isFetching) && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-gray-500 animate-pulse">
            Searching…
          </span>
        )}
      </div>

      {query.length > 0 && query.length < 3 && (
        <p className="text-xs text-gray-500 mb-4">
          Type at least 3 characters to search.
        </p>
      )}

      {isError && (
        <div className="text-center py-10 text-sm text-red-400">
          Search failed. Check your connection and try again.
        </div>
      )}

      {data && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-gray-500">
            {data.total} result{data.total !== 1 ? "s" : ""}
          </span>
          {method && (
            <span className="flex items-center gap-1 text-xs text-gray-600">
              <Cpu className="h-3 w-3" />
              {method === "semantic" ? "Semantic (embedding)" : "Keyword fallback"}
            </span>
          )}
        </div>
      )}

      {results.length === 0 && data && query.length >= 3 && (
        <div className="text-center py-12 text-gray-500 text-sm">
          No results found for <em className="text-gray-400">"{query}"</em>.
        </div>
      )}

      <div className="flex flex-col gap-2">
        {results.map((alert) => (
          <Link
            key={alert.id}
            to={`/alerts/${alert.id}`}
            className="bg-[#111827] border border-gray-800 rounded-lg px-4 py-3 flex items-start gap-3 hover:border-gray-600 transition-colors"
          >
            <SeverityBadge severity={alert.severity} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate font-medium">{alert.title}</p>
              {alert.description && (
                <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
                  {alert.description.slice(0, 200)}
                </p>
              )}
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                <span>{alert.source_name}</span>
                <span>{formatDateTime(alert.normalized_at)}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
