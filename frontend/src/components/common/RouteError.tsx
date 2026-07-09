import { useRouteError } from "react-router-dom";
import ErrorMessage from "./ErrorMessage";

/**
 * Route-level error fallback. The app-level ErrorBoundary never sees
 * render errors inside routes (React Router catches them first), so
 * without an errorElement users get the router's default developer
 * error screen.
 */
export default function RouteError() {
  const error = useRouteError();
  const detail = error instanceof Error ? error.message : undefined;

  return (
    <div>
      <ErrorMessage
        message="Something went wrong rendering this page."
        onRetry={() => window.location.reload()}
      />
      {detail && (
        <p className="text-center text-xs text-gray-600 -mt-4">{detail}</p>
      )}
    </div>
  );
}
