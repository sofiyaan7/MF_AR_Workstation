/**
 * Route guards.
 *
 * These are a usability layer: they route people sensibly and avoid rendering
 * pages that would only 403. Authorisation itself lives on the server, which
 * re-checks the caller's role on every single request.
 */
import { Loader2 } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/hooks/use-auth";

function FullPageLoader() {
  return (
    <div className="flex h-full items-center justify-center" role="status" aria-live="polite">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Requires a signed-in session; forces a password change when one is pending. */
export function RequireAuth() {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (mustChangePassword && location.pathname !== "/security") {
    return <Navigate to="/security" replace />;
  }
  return <Outlet />;
}

/** Requires an administrator role. */
export function RequireAdmin() {
  const { isAdmin, isLoading } = useAuth();

  if (isLoading) return <FullPageLoader />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <Outlet />;
}
