import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-blue-600/20 p-3 rounded-full mb-4">
            <Shield className="h-8 w-8 text-blue-400" />
          </div>
          <h1 className="text-xl font-semibold text-white">CTI Summarizer</h1>
          <p className="text-sm text-gray-400 mt-1">Sign in to your account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[#111827] border border-gray-800 rounded-lg p-6 space-y-4"
        >
          <div>
            <label className="block text-xs text-gray-400 mb-1.5" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium rounded-md py-2 transition-colors"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-4 bg-gray-900/60 border border-gray-800 rounded-md px-4 py-3">
          <p className="text-xs text-gray-500 leading-relaxed">
            <span className="text-gray-400 font-medium">First time?</span> Run{" "}
            <code className="text-blue-400 bg-gray-800 px-1 rounded text-[11px]">
              python -m scripts.setup_db
            </code>{" "}
            to create the database, then sign in with{" "}
            <code className="text-blue-400 bg-gray-800 px-1 rounded text-[11px]">
              admin
            </code>{" "}
            /{" "}
            <code className="text-blue-400 bg-gray-800 px-1 rounded text-[11px]">
              changeme
            </code>
            . Create additional users from the Admin panel after logging in.
          </p>
        </div>
      </div>
    </div>
  );
}
