import { AlertTriangle } from "lucide-react";

interface Props {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorMessage({
  message = "Failed to load data",
  onRetry,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
      <AlertTriangle className="h-8 w-8 text-red-400" />
      <p className="text-gray-400 text-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-blue-400 hover:text-blue-300 underline"
        >
          Try again
        </button>
      )}
    </div>
  );
}
