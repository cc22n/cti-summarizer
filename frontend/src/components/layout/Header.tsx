import type React from "react";
import { LogOut, Menu, User } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useSidebar } from "../../contexts/SidebarContext";

interface Props {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export default function Header({ title, subtitle, actions }: Props) {
  const { user, logout } = useAuth();
  const { toggle } = useSidebar();

  return (
    <div className="flex items-start justify-between mb-6">
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          className="lg:hidden p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          aria-label="Toggle navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-semibold text-white">{title}</h1>
          {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {actions && <div className="flex items-center gap-2">{actions}</div>}

        {user && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <User className="h-3.5 w-3.5" />
              <span>{user.username}</span>
              <span className="bg-gray-800 text-gray-500 rounded px-1.5 py-0.5">
                {user.role}
              </span>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded-md px-2 py-1 transition-colors"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
