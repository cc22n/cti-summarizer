import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Shield,
  Radio,
  FileText,
  Database,
  TrendingUp,
  GitMerge,
  SearchCode,
  Users,
} from "lucide-react";
import { useRealtimeAlerts } from "../../hooks/useRealtimeAlerts";
import { useSidebar } from "../../contexts/SidebarContext";
import { useAuth } from "../../contexts/AuthContext";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/alerts", icon: Shield, label: "Alerts" },
  { to: "/sources", icon: Radio, label: "Sources" },
  { to: "/summaries", icon: FileText, label: "Summaries" },
  { to: "/predictions", icon: TrendingUp, label: "Predictions" },
  { to: "/correlations", icon: GitMerge, label: "Correlations" },
  { to: "/search", icon: SearchCode, label: "Semantic Search" },
];

export default function Sidebar() {
  const { newCount, clearCount } = useRealtimeAlerts();
  const { open, close } = useSidebar();
  const { user } = useAuth();

  return (
    <aside
      className={`w-56 shrink-0 bg-[#111827] border-r border-gray-800 flex flex-col
        fixed inset-y-0 left-0 z-30 transition-transform duration-200
        lg:relative lg:translate-x-0 lg:z-auto
        ${open ? "translate-x-0" : "-translate-x-full"}`}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-800">
        <Database className="h-5 w-5 text-blue-400" />
        <span className="text-sm font-semibold text-white tracking-tight">
          CTI Summarizer
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-3 flex-1">
        {NAV.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => {
              if (label === "Alerts") clearCount();
              close();
            }}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? "bg-blue-600/20 text-blue-400 font-medium"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`
            }
          >
            <Icon className="h-4 w-4" />
            <span className="flex-1">{label}</span>
            {label === "Alerts" && newCount > 0 && (
              <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                {newCount > 99 ? "99+" : newCount}
              </span>
            )}
          </NavLink>
        ))}

        {user?.role === "admin" && (
          <>
            <div className="my-1 border-t border-gray-800/60" />
            <NavLink
              to="/admin"
              onClick={close}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400 font-medium"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`
              }
            >
              <Users className="h-4 w-4" />
              <span className="flex-1">Admin</span>
            </NavLink>
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-xs text-gray-600">CTI Summarizer v0.2.0</p>
      </div>
    </aside>
  );
}
