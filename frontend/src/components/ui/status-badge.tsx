import { Badge } from "@/components/ui/badge";
import type { AccountStatus, ProjectStatus, Visibility } from "@/types";

const PROJECT_STATUS = {
  ACTIVE: { label: "Active", variant: "success", dot: "bg-success" },
  MAINTENANCE: { label: "Maintenance", variant: "warning", dot: "bg-warning" },
  DEPRECATED: { label: "Deprecated", variant: "destructive", dot: "bg-destructive" },
  COMING_SOON: { label: "Coming soon", variant: "secondary", dot: "bg-muted-foreground" },
} as const;

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const config = PROJECT_STATUS[status] ?? PROJECT_STATUS.ACTIVE;
  return (
    <Badge variant={config.variant}>
      <span className={`size-1.5 rounded-full ${config.dot}`} aria-hidden />
      {config.label}
    </Badge>
  );
}

const ACCOUNT_STATUS = {
  ACTIVE: { label: "Active", variant: "success" },
  DISABLED: { label: "Disabled", variant: "muted" },
  LOCKED: { label: "Locked", variant: "destructive" },
  PENDING_PASSWORD_CHANGE: { label: "Pending password", variant: "warning" },
} as const;

export function AccountStatusBadge({ status }: { status: AccountStatus }) {
  const config = ACCOUNT_STATUS[status] ?? ACCOUNT_STATUS.ACTIVE;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

const VISIBILITY = {
  ALL_EMPLOYEES: { label: "All employees", variant: "outline" },
  SPECIFIC_EMPLOYEES: { label: "Specific employees", variant: "default" },
  ADMIN_ONLY: { label: "Admins only", variant: "warning" },
} as const;

export function VisibilityBadge({ visibility }: { visibility: Visibility }) {
  const config = VISIBILITY[visibility] ?? VISIBILITY.ALL_EMPLOYEES;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

const ROLE = {
  SUPER_ADMIN: { label: "Super admin", variant: "default" },
  ADMIN: { label: "Admin", variant: "default" },
  USER: { label: "Employee", variant: "muted" },
} as const;

export function RoleBadge({ role }: { role: keyof typeof ROLE }) {
  const config = ROLE[role] ?? ROLE.USER;
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
