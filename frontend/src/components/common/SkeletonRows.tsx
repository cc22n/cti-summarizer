interface Props {
  rows?: number;
  cols?: number;
}

function SkeletonCell({ wide }: { wide?: boolean }) {
  return (
    <div
      className={`h-3 bg-gray-800 rounded animate-pulse ${wide ? "w-48" : "w-20"}`}
    />
  );
}

export default function SkeletonRows({ rows = 5, cols = 4 }: Props) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="border-b border-gray-800">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <SkeletonCell wide={j === 0} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 space-y-3">
      <div className="h-3 bg-gray-800 rounded animate-pulse w-24" />
      <div className="h-6 bg-gray-800 rounded animate-pulse w-16" />
      <div className="h-2 bg-gray-800 rounded animate-pulse w-32" />
    </div>
  );
}
