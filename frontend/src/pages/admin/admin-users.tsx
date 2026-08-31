import {
  Activity, Ban, CheckCircle2, History, KeyRound, MoreHorizontal, Pencil, Search,
  Trash2, Unlock, UserPlus,
} from "lucide-react";
import * as React from "react";

import { CredentialDialog, UserFormDialog } from "@/components/admin/user-form";
import { UserActivityDialog } from "@/components/admin/user-activity-dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { AccountStatusBadge, RoleBadge } from "@/components/ui/status-badge";
import { useAuth } from "@/hooks/use-auth";
import { useDebounce } from "@/hooks/use-debounce";
import { useAdminUsers, useDepartments, useUserMutations } from "@/hooks/use-admin";
import { formatNumber, formatRelative } from "@/lib/format";
import { initials } from "@/lib/utils";
import type { UserAdminView } from "@/types";

const ALL = "__all__";

type Credential = { employeeId: string; password: string; name: string };

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();

  const [search, setSearch] = React.useState("");
  const [department, setDepartment] = React.useState(ALL);
  const [role, setRole] = React.useState(ALL);
  const [status, setStatus] = React.useState(ALL);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<UserAdminView | null>(null);
  const [credential, setCredential] = React.useState<Credential | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<UserAdminView | null>(null);
  const [resetTarget, setResetTarget] = React.useState<UserAdminView | null>(null);
  const [activityTarget, setActivityTarget] = React.useState<{ user: UserAdminView; tab: "activity" | "logins" } | null>(null);

  const debouncedSearch = useDebounce(search, 250);
  const { data: departments } = useDepartments();
  const { setEnabled, unlock, resetPassword, remove } = useUserMutations();

  const query = React.useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      department: department !== ALL ? department : undefined,
      role: role !== ALL ? role : undefined,
      status: status !== ALL ? status : undefined,
      limit: 200,
      sort: "name",
    }),
    [debouncedSearch, department, role, status],
  );

  const { data, isLoading, error, refetch } = useAdminUsers(query);

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (user: UserAdminView) => {
    setEditing(user);
    setFormOpen(true);
  };

  const handleReset = async () => {
    if (!resetTarget) return;
    const target = resetTarget;
    setResetTarget(null);
    const result = await resetPassword.mutateAsync(target.id);
    setCredential({
      employeeId: result.employee_id,
      password: result.temporary_password,
      name: target.full_name,
    });
  };

  return (
    <div>
      <PageHeader
        title="Users"
        description="Only employees listed here can sign in to the portal."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }, { label: "Users" }]}
        actions={
          <Button onClick={openCreate}>
            <UserPlus />
            Add employee
          </Button>
        }
      />

      <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, Employee ID or email…"
            aria-label="Search employees"
            className="pl-9"
          />
        </div>
        <Select value={department} onValueChange={setDepartment}>
          <SelectTrigger className="lg:w-44" aria-label="Filter by department">
            <SelectValue placeholder="All departments" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All departments</SelectItem>
            {(departments ?? []).map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="lg:w-40" aria-label="Filter by role">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All roles</SelectItem>
            <SelectItem value="USER">Employee</SelectItem>
            <SelectItem value="ADMIN">Administrator</SelectItem>
            <SelectItem value="SUPER_ADMIN">Super administrator</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="lg:w-44" aria-label="Filter by status">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="DISABLED">Disabled</SelectItem>
            <SelectItem value="LOCKED">Locked</SelectItem>
            <SelectItem value="PENDING_PASSWORD_CHANGE">Pending password</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && <TableSkeleton rows={8} columns={7} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && data && data.items.length === 0 && (
        <EmptyState
          title={search ? "No employees match your search" : "No employees yet"}
          description={
            search
              ? "Try a different name, Employee ID or email."
              : "Add the first employee so they can sign in to the portal."
          }
          action={
            !search ? (
              <Button onClick={openCreate}>
                <UserPlus />
                Add employee
              </Button>
            ) : undefined
          }
        />
      )}

      {!isLoading && !error && data && data.items.length > 0 && (
        <div className="surface overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last login</TableHead>
                <TableHead className="text-right">Logins</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((user) => {
                const isSelf = user.id === currentUser?.id;
                return (
                  <TableRow key={user.id}>
                    <TableCell className="font-mono text-sm">{user.employee_id}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <span
                          className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-2xs font-semibold text-muted-foreground"
                          aria-hidden
                        >
                          {initials(user.full_name)}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {user.full_name}
                            {isSelf && (
                              <span className="ml-1.5 text-2xs font-normal text-muted-foreground">
                                (you)
                              </span>
                            )}
                          </p>
                          <p className="truncate text-2xs text-muted-foreground">{user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {user.department ?? "—"}
                    </TableCell>
                    <TableCell>
                      <RoleBadge role={user.role} />
                    </TableCell>
                    <TableCell>
                      <AccountStatusBadge status={user.status} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                      {user.last_login_at ? formatRelative(user.last_login_at) : "Never"}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {formatNumber(user.login_count)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Actions for ${user.full_name}`}
                          >
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onSelect={() => openEdit(user)}>
                            <Pencil />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onSelect={() => setActivityTarget({ user, tab: "activity" })}
                          >
                            <Activity />
                            View activity
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onSelect={() => setActivityTarget({ user, tab: "logins" })}
                          >
                            <History />
                            Login history
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onSelect={() => setResetTarget(user)}>
                            <KeyRound />
                            Reset password
                          </DropdownMenuItem>
                          {user.locked_until && (
                            <DropdownMenuItem onSelect={() => unlock.mutate(user.id)}>
                              <Unlock />
                              Unlock account
                            </DropdownMenuItem>
                          )}
                          {user.is_active ? (
                            <DropdownMenuItem
                              destructive
                              disabled={isSelf}
                              onSelect={() => setEnabled.mutate({ id: user.id, enabled: false })}
                            >
                              <Ban />
                              Disable
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem
                              onSelect={() => setEnabled.mutate({ id: user.id, enabled: true })}
                            >
                              <CheckCircle2 />
                              Enable
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            destructive
                            disabled={isSelf}
                            onSelect={() => setDeleteTarget(user)}
                          >
                            <Trash2 />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <UserFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        user={editing}
        departments={departments ?? []}
        onCredentialIssued={setCredential}
      />

      <CredentialDialog credential={credential} onClose={() => setCredential(null)} />

      <UserActivityDialog
        target={activityTarget}
        onClose={() => setActivityTarget(null)}
      />

      <AlertDialog open={resetTarget !== null} onOpenChange={(open) => !open && setResetTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset password for {resetTarget?.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              A new temporary password is generated and shown once. Their current password
              stops working immediately and all their sessions are signed out.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReset}>Reset password</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {deleteTarget?.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              They can no longer sign in and are removed from the employee list. This is a
              soft delete — their activity history stays in the audit log for reference.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              destructive
              onClick={() => {
                if (deleteTarget) remove.mutate(deleteTarget.id);
                setDeleteTarget(null);
              }}
            >
              Remove employee
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
