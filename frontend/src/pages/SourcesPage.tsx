import { useSources } from "../hooks/useSources";
import Header from "../components/layout/Header";
import SourceCard from "../components/sources/SourceCard";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";

export default function SourcesPage() {
  const { data: sources, isLoading, error, refetch } = useSources();

  return (
    <div>
      <Header
        title="Sources"
        subtitle="CTI feed sources and ingestion status"
      />

      {isLoading && <LoadingSpinner text="Loading sources..." />}
      {error && <ErrorMessage onRetry={refetch} />}

      {sources && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sources.map((source) => (
            <SourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
