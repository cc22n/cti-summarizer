import { useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import {
  useLatestDigest,
  useSummaries,
  useGenerateDigest,
} from "../hooks/useSummaries";
import Header from "../components/layout/Header";
import DigestCard from "../components/summaries/DigestCard";
import SummaryCard from "../components/summaries/SummaryCard";
import Pagination from "../components/common/Pagination";
import LoadingSpinner from "../components/common/LoadingSpinner";

export default function SummariesPage() {
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<"" | "alert" | "digest">("");

  const { data: latestDigest, isLoading: digestLoading } = useLatestDigest();
  const { data, isLoading } = useSummaries({
    page,
    page_size: 20,
    summary_type: filter || undefined,
  });
  const {
    mutate: generateDigest,
    isPending: generating,
    isSuccess: digestQueued,
  } = useGenerateDigest();

  const selectClass =
    "bg-[#1f2937] border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-blue-500 mb-4";

  return (
    <div>
      <Header
        title="Summaries"
        subtitle="LLM-generated threat intelligence summaries"
        actions={
          <button
            onClick={() => generateDigest(24)}
            disabled={generating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white border border-gray-700 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileText className="h-3.5 w-3.5" />
            )}
            {generating ? "Queuing…" : "Generate Digest"}
          </button>
        }
      />

      {digestQueued && (
        <p className="text-xs text-green-400 mb-3">
          Digest generation queued. Results will appear shortly.
        </p>
      )}

      <DigestCard digest={latestDigest} isLoading={digestLoading} />

      <div className="flex items-center gap-3 mb-4">
        <select
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value as typeof filter);
            setPage(1);
          }}
          className={selectClass}
        >
          <option value="">All summaries</option>
          <option value="alert">Per-alert</option>
          <option value="digest">Digests</option>
        </select>
        {data && (
          <span className="text-xs text-gray-500 mb-4">
            {data.total} {data.total === 1 ? "summary" : "summaries"}
          </span>
        )}
      </div>

      {isLoading && <LoadingSpinner text="Loading summaries..." />}

      {!isLoading && data?.items.length === 0 && (
        <div className="bg-[#111827] border border-gray-800 rounded-lg p-10 text-center">
          <FileText className="h-8 w-8 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">No summaries yet.</p>
          <p className="text-gray-600 text-xs mt-1">
            Click "Generate Digest" to create an AI summary of recent threats.
          </p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="flex flex-col gap-3">
            {data.items.map((s) => (
              <SummaryCard key={s.id} summary={s} />
            ))}
          </div>
          <div className="mt-4">
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={setPage}
            />
          </div>
        </>
      )}
    </div>
  );
}
