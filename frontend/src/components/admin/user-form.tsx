/** Create / edit an employee account, and the one-time password reveal. */
import { Check, Copy, KeyRound, UserPlus } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/hooks/use-auth";
import { useUserMutations } from "@/hooks/use-admin";
import type { AccountStatus, Role, UserAdminView } from "@/types";

interface UserFormValues {
  employee_id: string;
  full_name: string;
  email: string;
  department: string;
  job_title: string;
  phone: string;
  role: Role;
  status: AccountStatus;
  temporary_password: string;
  require_password_change: boolean;
  notes: string;
}

function emptyForm(): UserFormValues {
  return {
    employee_id: "",
    full_name: "",
    email: "",
    department: "",
    job_title: "",
    phone: "",
    role: "USER",
    status: "ACTIVE",
    temporary_password: "",
    require_password_change: true,
    notes: "",
  };
}

function fromUser(user: UserAdminView): UserFormValues {
  return {
    employee_id: user.employee_id,
    full_name: user.full_name,
    email: user.email,
    department: user.department ?? "",
    job_title: user.job_title ?? "",
    phone: user.phone ?? "",
    role: user.role,
    status: user.status,
    temporary_password: "",
    require_password_change: false,
    notes: user.notes ?? "",
  };
}

/**
 * Shows a generated password exactly once.
 *
 * The portal stores only the Argon2 hash, so this dialog is the sole
 * opportunity to copy the credential before it is unrecoverable.
 */
export function CredentialDialog({
  credential,
  onClose,
}: {
  credential: { employeeId: string; password: string; name?: string } | null;
  onClose: () => void;
}) {
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => setCopied(false), [credential]);

  const copy = async () => {
    if (!credential) return;
    try {
      await navigator.clipboard.writeText(credential.password);
      setCopied(true);
      toast.success("Password copied to clipboard");
    } catch {
      toast.error("Could not copy — select the password and copy it manually.");
    }
  };

  return (
    <Dialog open={credential !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="size-4" />
            Temporary password
          </DialogTitle>
          <DialogDescription>
            Share this with {credential?.name ?? credential?.employeeId} over a secure channel.
            It is shown once and cannot be retrieved again.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <p className="text-xs text-muted-foreground">Employee ID</p>
            <p className="font-mono text-sm font-medium text-foreground">
              {credential?.employeeId}
            </p>
          </div>
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Temporary password</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 select-all break-all rounded-md border border-border bg-muted px-3 py-2 font-mono text-sm">
                {credential?.password}
              </code>
              <Button variant="outline" size="icon" onClick={copy} aria-label="Copy password">
                {copied ? <Check className="text-success" /> : <Copy />}
              </Button>
            </div>
          </div>
          <p className="rounded-md border border-warning/25 bg-warning/10 px-3 py-2 text-xs text-muted-foreground">
            They must change this password at first sign-in before they can use the portal.
          </p>
        </div>

        <DialogFooter>
          <Button onClick={onClose}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface UserFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: UserAdminView | null;
  departments?: string[];
  onCredentialIssued: (credential: { employeeId: string; password: string; name: string }) => void;
}

export function UserFormDialog({
  open, onOpenChange, user, departments = [], onCredentialIssued,
}: UserFormDialogProps) {
  const isEdit = Boolean(user);
  const { user: currentUser } = useAuth();
  const { create, update } = useUserMutations();
  const [values, setValues] = React.useState<UserFormValues>(emptyForm);
  const [touched, setTouched] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setValues(user ? fromUser(user) : emptyForm());
      setTouched(false);
    }
  }, [open, user]);

  const set = <K extends keyof UserFormValues>(key: K, value: UserFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  const idValid = /^[A-Za-z0-9_-]{2,64}$/.test(values.employee_id.trim());
  const nameValid = values.full_name.trim().length >= 2;
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim());
  const canSubmit =
    (isEdit || idValid) && nameValid && emailValid && !create.isPending && !update.isPending;

  // Only a super admin may grant the super-admin role; the API enforces this too.
  const canGrantSuperAdmin = currentUser?.role === "SUPER_ADMIN";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!canSubmit) return;

    try {
      if (isEdit && user) {
        await update.mutateAsync({
          id: user.id,
          payload: {
            full_name: values.full_name.trim(),
            email: values.email.trim(),
            department: values.department.trim() || null,
            job_title: values.job_title.trim() || null,
            phone: values.phone.trim() || null,
            role: values.role,
            status: values.status,
            notes: values.notes.trim() || null,
          },
        });
      } else {
        const result = await create.mutateAsync({
          employee_id: values.employee_id.trim().toUpperCase(),
          full_name: values.full_name.trim(),
          email: values.email.trim(),
          department: values.department.trim() || null,
          job_title: values.job_title.trim() || null,
          phone: values.phone.trim() || null,
          role: values.role,
          status: values.status,
          require_password_change: values.require_password_change,
          notes: values.notes.trim() || null,
          ...(values.temporary_password
            ? { temporary_password: values.temporary_password }
            : {}),
        });
        if (result.temporary_password) {
          onCredentialIssued({
            employeeId: result.user.employee_id,
            password: result.temporary_password,
            name: result.user.full_name,
          });
        }
      }
      onOpenChange(false);
    } catch {
      // The mutation already reported the error; keep the dialog open.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Edit ${user?.full_name}` : "Add employee"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Employee ID cannot be changed once an account exists."
              : "Only employees added here can sign in to the portal."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="user-employee-id" required={!isEdit}>
                Employee ID
              </Label>
              <Input
                id="user-employee-id"
                value={values.employee_id}
                onChange={(event) => set("employee_id", event.target.value.toUpperCase())}
                placeholder="ARWL12345"
                className="font-mono"
                disabled={isEdit}
                aria-invalid={touched && !isEdit && !idValid}
                required={!isEdit}
              />
              {touched && !isEdit && !idValid && (
                <p className="text-xs text-destructive">
                  Use 2–64 letters, numbers, hyphens or underscores.
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="user-full-name" required>
                Full name
              </Label>
              <Input
                id="user-full-name"
                value={values.full_name}
                onChange={(event) => set("full_name", event.target.value)}
                placeholder="Sofiyaan Sameer"
                aria-invalid={touched && !nameValid}
                required
              />
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="user-email" required>
                Email
              </Label>
              <Input
                id="user-email"
                type="email"
                value={values.email}
                onChange={(event) => set("email", event.target.value)}
                placeholder="sofiyaan.sameer@example.com"
                aria-invalid={touched && !emailValid}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="user-department">Department</Label>
              <Input
                id="user-department"
                value={values.department}
                onChange={(event) => set("department", event.target.value)}
                placeholder="Research"
                list="department-options"
              />
              <datalist id="department-options">
                {departments.map((department) => (
                  <option key={department} value={department} />
                ))}
              </datalist>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="user-job-title">Job title</Label>
              <Input
                id="user-job-title"
                value={values.job_title}
                onChange={(event) => set("job_title", event.target.value)}
                placeholder="Analyst"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="user-role">Role</Label>
              <Select value={values.role} onValueChange={(value) => set("role", value as Role)}>
                <SelectTrigger id="user-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USER">Employee</SelectItem>
                  <SelectItem value="ADMIN">Administrator</SelectItem>
                  {canGrantSuperAdmin && <SelectItem value="SUPER_ADMIN">Super administrator</SelectItem>}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Administrators can manage users, projects and view all activity.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="user-status">Account status</Label>
              <Select
                value={values.status}
                onValueChange={(value) => set("status", value as AccountStatus)}
              >
                <SelectTrigger id="user-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="DISABLED">Disabled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {!isEdit && (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="user-temp-password">Temporary password</Label>
                  <Input
                    id="user-temp-password"
                    value={values.temporary_password}
                    onChange={(event) => set("temporary_password", event.target.value)}
                    placeholder="Leave blank to generate a strong password"
                    className="font-mono"
                    autoComplete="off"
                  />
                  <p className="text-xs text-muted-foreground">
                    If left blank, the portal generates one and shows it to you once.
                  </p>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <Label htmlFor="user-require-change">Require password change</Label>
                    <p className="text-xs text-muted-foreground">
                      The employee must set their own password before using the portal.
                    </p>
                  </div>
                  <Switch
                    id="user-require-change"
                    checked={values.require_password_change}
                    onCheckedChange={(checked) => set("require_password_change", checked)}
                  />
                </div>
              </div>
            </>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="user-notes">Internal notes</Label>
            <Textarea
              id="user-notes"
              value={values.notes}
              onChange={(event) => set("notes", event.target.value)}
              placeholder="Visible only to administrators (optional)"
              rows={2}
              maxLength={2000}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {!create.isPending && !update.isPending && <UserPlus />}
              {isEdit ? "Save changes" : "Create user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
