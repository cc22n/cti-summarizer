import { BookOpen, Zap, Loader2 } from "lucide-react";
import type { Summary } from "../../types/summary";
import { formatDateTime } from "../../lib/formatters";
import { useGenerateDigest } from "../../hooks/useSummaries";

interface Props {
  digest: Summary | null | undefined;
  isLoading?: boolean;
}

export default function DigestCard({ digest, isLoading }: Props) {
  const { mutate: generate, isPending, data: result } = useGenerateDigest();

  return (
    <div className="bg-[#111827] border border-blue-500/20 rounded-lg mb-6">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-blue-400" />
          <h3 className="text-sm font-medium text-white">Latest Digest</h3>
          {digest && (
            <span className="text-xs text-gray-500">
              {formatDateTime(digest.created_at)}
            </span>
          )}
        </div>
        <button
          onClick={() => generate(24)}
          disabled={isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Zap className="h-3 w-3" />
          )}
          Generate (24h)
        </button>
      </div>

      {/* Content */}
      <div className="px-5 py-4">
        {isLoading && (
          <p className="text-sm text-gray-500 animate-pulse">Loading...</p>
        )}
        {!isLoading && !digest && !result && (
          <p className="text-sm text-gray-500">
            No digest yet. Click "Generate" to create one.
          </p>
        )}
        {result?.data && (
          <p className="text-xs text-green-400 mb-3">
            Digest queued — task ID: {result.data.task_id}
          </p>
        )}
        {digest && (
          <div>
            <div className="prose prose-invert prose-sm max-w-none">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed font-sans">
                {digest.content}
              </pre>
            </div>
            {digest.prompt_tokens && (
              <p className="text-xs text-gray-600 mt-3">
                {digest.prompt_tokens} prompt + {digest.completion_tokens} completion tokens
                &nbsp;·&nbsp; {digest.model_used}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
