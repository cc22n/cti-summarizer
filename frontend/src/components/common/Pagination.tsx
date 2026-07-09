import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, pages, total, onPageChange }: Props) {
  if (pages <= 1) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
      <p className="text-xs text-gray-500">
        {total} total
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
          className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-xs text-gray-400">
          {page} / {pages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          aria-label="Next page"
          className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
