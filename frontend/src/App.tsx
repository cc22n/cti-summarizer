import { lazy, Suspense } from "react";
import { Navigate, createBrowserRouter, RouterProvider } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/layout/Layout";
import LoginPage from "./pages/LoginPage";
import ErrorBoundary from "./components/common/ErrorBoundary";
import LoadingSpinner from "./components/common/LoadingSpinner";
import RouteError from "./components/common/RouteError";

// Pages are lazy-loaded so heavy chart dependencies (Recharts) are split
// out of the initial bundle and fetched per route.
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const AlertDetailPage = lazy(() => import("./pages/AlertDetailPage"));
const SummariesPage = lazy(() => import("./pages/SummariesPage"));
const SourcesPage = lazy(() => import("./pages/SourcesPage"));
const PredictionsPage = lazy(() => import("./pages/PredictionsPage"));
const CorrelationsPage = lazy(() => import("./pages/CorrelationsPage"));
const SemanticSearchPage = lazy(() => import("./pages/SemanticSearchPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

function withSuspense(node: React.ReactNode) {
  return (
    <Suspense fallback={<LoadingSpinner text="Loading page..." />}>
      {node}
    </Suspense>
  );
}

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
    errorElement: <RouteError />,
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    errorElement: <RouteError />,
    children: [
      {
        // Pathless wrapper: render errors from any page bubble here, so the
        // fallback shows inside the Layout (sidebar stays) instead of React
        // Router's default developer error screen.
        errorElement: <RouteError />,
        children: [
          { index: true, element: withSuspense(<DashboardPage />) },
          { path: "alerts", element: withSuspense(<AlertsPage />) },
          { path: "alerts/:id", element: withSuspense(<AlertDetailPage />) },
          { path: "summaries", element: withSuspense(<SummariesPage />) },
          { path: "sources", element: withSuspense(<SourcesPage />) },
          { path: "predictions", element: withSuspense(<PredictionsPage />) },
          { path: "correlations", element: withSuspense(<CorrelationsPage />) },
          { path: "search", element: withSuspense(<SemanticSearchPage />) },
          {
            path: "admin",
            element: (
              <RequireAdmin>{withSuspense(<AdminPage />)}</RequireAdmin>
            ),
          },
        ],
      },
    ],
  },
  { path: "*", element: withSuspense(<NotFoundPage />), errorElement: <RouteError /> },
]);

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
