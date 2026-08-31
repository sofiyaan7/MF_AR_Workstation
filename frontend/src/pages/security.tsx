import { AlertTriangle, Check, Eye, EyeOff, KeyRound, ShieldCheck, X } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/hooks/use-auth";
import { formatDateTime, formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { authApi } from "@/services/endpoints";

/** Client-side mirror of the server policy — the server remains authoritative. */
function checkRules(password: string, minLength: number) {
  return [
    { label: `At least ${minLength} characters`, met: password.length >= minLength },
    { label: "An uppercase letter", met: /[A-Z]/.test(password) },
    { label: "A lowercase letter", met: /[a-z]/.test(password) },
    { label: "A number", met: /[0-9]/.test(password) },
    { label: "A special character", met: /[^A-Za-z0-9]/.test(password) },
  ];
}

function PasswordInput({
  id, label, value, onChange, autoComplete,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
}) {
  const [visible, setVisible] = React.useState(false);
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} required>
        {label}
      </Label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          required
          className="pr-10"
        />
        <button
          type="button"
          onClick={() => setVisible((shown) => !shown)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    </div>
  );
}

export function SecurityPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [minLength, setMinLength] = React.useState(12);
  const [submitting, setSubmitting] = React.useState(false);
  const [errors, setErrors] = React.useState<string[]>([]);

  React.useEffect(() => {
    authApi
      .passwordPolicy()
      .then((policy) => setMinLength(policy.min_length))
      .catch(() => undefined);
  }, []);

  const rules = checkRules(newPassword, minLength);
  const allMet = rules.every((rule) => rule.met);
  const matches = newPassword.length > 0 && newPassword === confirmPassword;
  const canSubmit = Boolean(currentPassword) && allMet && matches && !submitting;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrors([]);
    setSubmitting(true);
    try {
      const response = await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast.success(response.message, { description: response.detail ?? undefined });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await refreshUser();
      navigate("/");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.details.length ? error.details : [error.message]);
        toast.error(error.message);
      } else {
        setErrors(["Could not change your password. Please try again."]);
        toast.error("Could not change your password.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Security"
        description="Manage the password you use to sign in to the portal."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Security" }]}
      />

      {user?.must_change_password && (
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3"
        >
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
          <div>
            <p className="text-sm font-semibold text-foreground">Password change required</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
              You are signed in with a temporary password. Choose a new one to unlock the rest
              of the portal.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound className="size-4" />
              Change password
            </CardTitle>
            <CardDescription>
              Changing your password signs you out of every other device.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="max-w-md space-y-4">
              <PasswordInput
                id="current_password"
                label="Current password"
                value={currentPassword}
                onChange={setCurrentPassword}
                autoComplete="current-password"
              />
              <Separator />
              <PasswordInput
                id="new_password"
                label="New password"
                value={newPassword}
                onChange={setNewPassword}
                autoComplete="new-password"
              />
              <PasswordInput
                id="confirm_password"
                label="Confirm new password"
                value={confirmPassword}
                onChange={setConfirmPassword}
                autoComplete="new-password"
              />

              {confirmPassword.length > 0 && !matches && (
                <p className="text-xs text-destructive">Passwords do not match.</p>
              )}

              {errors.length > 0 && (
                <div
                  role="alert"
                  className="rounded-md border border-destructive/25 bg-destructive/5 px-3 py-2"
                >
                  <ul className="space-y-0.5 text-xs text-destructive">
                    {errors.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              )}

              <Button type="submit" loading={submitting} disabled={!canSubmit}>
                {!submitting && <ShieldCheck />}
                Change password
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Password requirements</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-1.5">
                {rules.map((rule) => (
                  <li key={rule.label} className="flex items-center gap-2 text-sm">
                    {rule.met ? (
                      <Check className="size-3.5 shrink-0 text-success" />
                    ) : (
                      <X className="size-3.5 shrink-0 text-muted-foreground" />
                    )}
                    <span className={cn(rule.met ? "text-foreground" : "text-muted-foreground")}>
                      {rule.label}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-muted-foreground">
                You also cannot reuse a recent password, or include your name or Employee ID.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Account security</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Password last changed</p>
                <p className="font-medium text-foreground">
                  {user?.password_changed_at
                    ? `${formatDateTime(user.password_changed_at)} (${formatRelative(user.password_changed_at)})`
                    : "Never"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Last sign-in</p>
                <p className="font-medium text-foreground">{formatDateTime(user?.last_login_at)}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
