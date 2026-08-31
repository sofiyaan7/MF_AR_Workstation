import { Building2, Calendar, IdCard, LogIn, Mail, Save, ShieldCheck, UserRound } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { RoleBadge, AccountStatusBadge } from "@/components/ui/status-badge";
import { useAuth } from "@/hooks/use-auth";
import { formatDateTime, formatNumber, formatRelative } from "@/lib/format";
import { initials } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { authApi } from "@/services/endpoints";

function Field({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="truncate text-sm font-medium text-foreground">{value}</div>
      </div>
    </div>
  );
}

export function ProfilePage() {
  const { user, setUser } = useAuth();
  const [fullName, setFullName] = React.useState(user?.full_name ?? "");
  const [email, setEmail] = React.useState(user?.email ?? "");
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setEmail(user.email);
    }
  }, [user]);

  if (!user) return null;

  const dirty = fullName.trim() !== user.full_name || email.trim() !== user.email;

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await authApi.updateProfile({
        full_name: fullName.trim(),
        email: email.trim(),
      });
      setUser(updated);
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not save your profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Profile"
        description="Your account details in the MF AR Workstation portal."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Profile" }]}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <span
                className="flex size-16 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground"
                aria-hidden
              >
                {initials(user.full_name)}
              </span>
              <p className="mt-3 text-base font-semibold text-foreground">{user.full_name}</p>
              <p className="font-mono text-sm text-muted-foreground">{user.employee_id}</p>
              <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                <RoleBadge role={user.role} />
                <AccountStatusBadge status={user.status} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Account details</CardTitle>
            <CardDescription>
              Employee ID, department and role are managed by your administrator.
            </CardDescription>
          </CardHeader>
          <CardContent className="divide-y divide-border pt-0">
            <Field icon={IdCard} label="Employee ID" value={<span className="font-mono">{user.employee_id}</span>} />
            <Field icon={UserRound} label="Full name" value={user.full_name} />
            <Field icon={Mail} label="Email" value={user.email} />
            <Field icon={Building2} label="Department" value={user.department || "Not set"} />
            <Field icon={ShieldCheck} label="Role" value={<RoleBadge role={user.role} />} />
            <Field icon={Calendar} label="Account created" value={formatDateTime(user.created_at)} />
            <Field
              icon={LogIn}
              label="Last sign-in"
              value={
                user.last_login_at
                  ? `${formatDateTime(user.last_login_at)} (${formatRelative(user.last_login_at)})`
                  : "This is your first session"
              }
            />
            <Field icon={LogIn} label="Total sign-ins" value={formatNumber(user.login_count)} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">Edit your details</CardTitle>
            <CardDescription>
              You can update your own name and email. Changes are recorded in the audit log.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  minLength={2}
                  maxLength={160}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" loading={saving} disabled={!dirty}>
                  {!saving && <Save />}
                  Save changes
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
