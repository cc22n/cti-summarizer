import type { Severity } from "../../types/alert";

const STYLES: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-400 border border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  low: "bg-green-500/20 text-green-400 border border-green-500/30",
  info: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
};

interface Props {
  severity: string;
  className?: string;
}

export default function SeverityBadge({ severity, className = "" }: Props) {
  const style = STYLES[severity as Severity] ?? STYLES.info;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide ${style} ${className}`}
    >
      {severity}
    </span>
  );
}
