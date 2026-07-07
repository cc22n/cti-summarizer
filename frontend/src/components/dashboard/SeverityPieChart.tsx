import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { PieSlice } from "../../lib/chartUtils";

interface Props {
  data: PieSlice[];
}

export default function SeverityPieChart({ data }: Props) {
  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-2">By Severity</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#1f2937",
              border: "1px solid #374151",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(v) => (
              <span style={{ color: "#9ca3af" }}>{v}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
