import { useState, type FormEvent } from "react";
import { UserPlus, Users, ShieldCheck, Eye, BarChart2 } from "lucide-react";
import { useUsers, useCreateUser } from "../hooks/useUsers";
import type { UserCreate } from "../types/auth";

const ROLE_OPTIONS: UserCreate["role"][] = ["admin", "analyst", "viewer"];

const ROLE_ICONS = {
  admin: ShieldCheck,
  analyst: BarChart2,
  viewer: Eye,
} as const;

const ROLE_COLORS = {
  admin: "text-red-400 bg-red-400/10",
  analyst: "text-blue-400 bg-blue-400/10",
  viewer: "text-gray-400 bg-gray-700/60",
} as const;

function RoleBadge({ role }: { role: string }) {
  const key = role as keyof typeof ROLE_COLORS;
  const Icon = ROLE_ICONS[key] ?? Eye;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium ${ROLE_COLORS[key] ?? ROLE_COLORS.viewer}`}
    >
      <Icon className="h-3 w-3" />
      {role}
    </span>
  );
}

export default function AdminPage() {
  const { data: users, isLoading, error } = useUsers();
  const createUser = useCreateUser();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserCreate["role"]>("analyst");
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccess(null);
    try {
      await createUser.mutateAsync({ username, password, role });
      setSuccess(`User "${username}" created successfully.`);
      setUsername("");
      setPassword("");
      setRole("analyst");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (typeof detail === "string") {
        setFormError(detail);
      } else if (Array.isArray(detail)) {
        setFormError((detail as { msg: string }[]).map((d) => d.msg).join(", "));
      } else {
        setFormError("Failed to create user. Username may already exist.");
      }
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-lg font-semibold text-white flex items-center gap-2">
          <Users className="h-5 w-5 text-blue-400" />
          User Management
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Create and view users. Only admins can access this page.
        </p>
      </div>

      {/* User list */}
      <section>
        <h2 className="text-sm font-medium text-gray-300 mb-3">Current Users</h2>
        {isLoading && (
          <p className="text-sm text-gray-500">Loading...</p>
        )}
        {error && (
          <p className="text-sm text-red-400">
            Failed to load users. Make sure JWT_SECRET_KEY is configured.
          </p>
        )}
        {users && (
          <div className="bg-[#111827] border border-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="text-left px-4 py-2.5">Username</th>
                  <th className="text-left px-4 py-2.5">Role</th>
                  <th className="text-left px-4 py-2.5">Status</th>
                  <th className="text-left px-4 py-2.5">Created</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-gray-800/60 last:border-0 hover:bg-gray-800/30"
                  >
                    <td className="px-4 py-2.5 text-gray-200 font-mono text-xs">
                      {u.username}
                    </td>
                    <td className="px-4 py-2.5">
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`text-[11px] font-medium ${u.is_active ? "text-green-400" : "text-gray-600"}`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Create user form */}
      <section>
        <h2 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <UserPlus className="h-4 w-4 text-blue-400" />
          Create New User
        </h2>
        <form
          onSubmit={handleCreate}
          className="bg-[#111827] border border-gray-800 rounded-lg p-5 space-y-4 max-w-sm"
        >
          <div>
            <label className="block text-xs text-gray-400 mb-1.5" htmlFor="new-username">
              Username
            </label>
            <input
              id="new-username"
              type="text"
              autoComplete="off"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={50}
              pattern="[a-zA-Z0-9_]+"
              title="Letters, digits, and underscores only"
              className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-600 mt-1">
              3-50 chars: letters, digits, underscores only.
            </p>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5" htmlFor="new-password">
              Password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-600 mt-1">
              Min 8 chars — include uppercase, lowercase, and a digit.
            </p>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5" htmlFor="new-role">
              Role
            </label>
            <select
              id="new-role"
              value={role}
              onChange={(e) => setRole(e.target.value as UserCreate["role"])}
              className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-blue-500"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-gray-600 mt-1">
              admin: full access &nbsp;|&nbsp; analyst: read + summarize &nbsp;|&nbsp; viewer: read-only
            </p>
          </div>

          {formError && (
            <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
              {formError}
            </p>
          )}
          {success && (
            <p className="text-xs text-green-400 bg-green-400/10 border border-green-400/20 rounded px-3 py-2">
              {success}
            </p>
          )}

          <button
            type="submit"
            disabled={createUser.isPending}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-md py-2 transition-colors"
          >
            {createUser.isPending ? "Creating..." : "Create User"}
          </button>
        </form>
      </section>
    </div>
  );
}
