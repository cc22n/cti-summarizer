import { Navigate, createBrowserRouter, RouterProvider } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/layout/Layout";
import DashboardPage from "./pages/DashboardPage";
import AlertsPage from "./pages/AlertsPage";
import AlertDetailPage from "./pages/AlertDetailPage";
import SummariesPage from "./pages/SummariesPage";
import SourcesPage from "./pages/SourcesPage";
import PredictionsPage from "./pages/PredictionsPage";
import CorrelationsPage from "./pages/CorrelationsPage";
import SemanticSearchPage from "./pages/SemanticSearchPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ErrorBoundary from "./components/common/ErrorBoundary";
import LoadingSpinner from "./components/common/LoadingSpinner";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner text="Restoring session..." />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner text="Restoring session..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "alerts", element: <AlertsPage /> },
      { path: "alerts/:id", element: <AlertDetailPage /> },
      { path: "summaries", element: <SummariesPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "predictions", element: <PredictionsPage /> },
      { path: "correlations", element: <CorrelationsPage /> },
      { path: "search", element: <SemanticSearchPage /> },
      {
        path: "admin",
        element: (
          <RequireAdmin>
            <AdminPage />
          </RequireAdmin>
        ),
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
