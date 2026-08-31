import { AlertCircle, BarChart3, Eye, EyeOff, LogIn, ShieldCheck } from "lucide-react";
import * as React from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { firstName } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { authApi } from "@/services/endpoints";

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [employeeId, setEmployeeId] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [forgotSent, setForgotSent] = React.useState(false);

  if (!isLoading && isAuthenticated) {
    const from = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(employeeId.trim(), password);
      toast.success(`Welcome back, ${firstName(user.full_name)}`);
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(user.must_change_password ? "/security" : from, { replace: true });
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : "Unable to sign in. Please try again.";
      setError(message);
      toast.error(message);
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPassword = async () => {
    if (!employeeId.trim()) {
      setError("Enter your Employee ID first, then choose “Forgot password”.");
      return;
    }
    try {
      const response = await authApi.forgotPassword(employeeId.trim());
      setForgotSent(true);
      toast.success(response.message, { description: response.detail ?? undefined });
    } catch {
      toast.error("Could not submit that request. Please contact your administrator.");
    }
  };

  return (
    <div className="flex min-h-full">
      {/* Brand panel — desktop only */}
      <div className="relative hidden w-1/2 flex-col justify-between bg-sidebar p-12 text-sidebar-foreground lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <BarChart3 className="size-5" strokeWidth={2.2} />
          </div>
          <div className="leading-tight">
            <p className="text-base font-semibold tracking-tight">MF AR Workstation</p>
            <p className="text-xs text-sidebar-muted">Internal project portal</p>
          </div>
        </div>

        <div className="max-w-md">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Every tool your team builds, in one place.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sidebar-muted">
            Dashboards, research tools and automations — launched from a single
            catalogue, with access controlled per employee and every action recorded.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-sidebar-muted">
            {[
              "Access limited to registered employees",
              "Per-project permissions enforced server-side",
              "Full activity and usage audit trail",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2.5">
                <ShieldCheck className="size-4 shrink-0 text-primary" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-2xs text-sidebar-muted">
          Authorised use only. Activity on this portal is monitored and logged.
        </p>
      </div>

      {/* Sign-in form */}
      <div className="flex w-full flex-col justify-center px-6 py-12 lg:w-1/2 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <BarChart3 className="size-5" strokeWidth={2.2} />
            </div>
            <div className="leading-tight">
              <p className="text-base font-semibold tracking-tight">MF AR Workstation</p>
              <p className="text-xs text-muted-foreground">Internal project portal</p>
            </div>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Sign in</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Use the Employee ID issued by your portal administrator.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="employee_id" required>
                Employee ID
              </Label>
              <Input
                id="employee_id"
                name="employee_id"
                value={employeeId}
                onChange={(event) => setEmployeeId(event.target.value)}
                placeholder="ARWL12345"
                autoComplete="username"
                autoCapitalize="characters"
                spellCheck={false}
                required
                autoFocus
                aria-invalid={Boolean(error)}
                className="font-mono tracking-wide"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" required>
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  required
                  aria-invalid={Boolean(error)}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-md border border-destructive/25 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {forgotSent && (
              <p className="rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
                Your request has been logged. An administrator will issue a temporary
                password — the portal does not email reset links.
              </p>
            )}

            <Button type="submit" className="w-full" loading={submitting} size="lg">
              {!submitting && <LogIn />}
              {submitting ? "Signing in…" : "Login"}
            </Button>

            <button
              type="button"
              onClick={handleForgotPassword}
              className="mx-auto block rounded text-xs text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Forgot password?
            </button>
          </form>

          <p className="mt-8 text-center text-2xs leading-relaxed text-muted-foreground">
            Access is restricted to employees registered by an administrator.
            Sign-in attempts are recorded.
          </p>
        </div>
      </div>
    </div>
  );
}
