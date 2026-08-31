import {
  Activity, BarChart3, FolderKanban, LayoutGrid, Clock, Settings, Shield,
  ShieldCheck, Star, Tags, Users, X, type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const MAIN_NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutGrid, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/favourites", label: "My Favourites", icon: Star },
  { to: "/recent", label: "Recently Used", icon: Clock },
  { to: "/activity", label: "My Activity", icon: Activity },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/projects", label: "Projects", icon: FolderKanban },
  { to: "/admin/categories", label: "Categories", icon: Tags },
  { to: "/admin/activity", label: "Activity Logs", icon: Activity },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
];

const SETTINGS_NAV: NavItem[] = [
  { to: "/profile", label: "Profile", icon: Settings },
  { to: "/security", label: "Security", icon: ShieldCheck },
];

function NavSection({ title, items, onNavigate }: { title?: string; items: NavItem[]; onNavigate?: () => void }) {
  return (
    <div className="space-y-0.5">
      {title && (
        <p className="px-3 pb-1.5 pt-3 text-2xs font-semibold uppercase tracking-wider text-sidebar-muted">
          {title}
        </p>
      )}
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar",
              isActive
                ? "bg-sidebar-accent text-sidebar-foreground"
                : "text-sidebar-muted hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <item.icon className={cn("size-4 shrink-0", isActive && "text-primary-foreground")} />
              <span className="truncate">{item.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </div>
  );
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { isAdmin } = useAuth();

  return (
    <>
      {/* Mobile scrim */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-[2px] transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
        aria-hidden
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-sidebar-border px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
              <BarChart3 className="size-4.5" strokeWidth={2.2} />
            </div>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-semibold tracking-tight">MF AR Workstation</p>
              <p className="truncate text-2xs text-sidebar-muted">Internal project portal</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            className="text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground lg:hidden"
            aria-label="Close navigation"
          >
            <X />
          </Button>
        </div>

        <nav
          aria-label="Main navigation"
          className="flex-1 space-y-1 overflow-y-auto p-3 scrollbar-thin"
        >
          <NavSection items={MAIN_NAV} onNavigate={onClose} />

          {/*
            Admin links are hidden from employees for clarity only. The backend
            rejects every admin request from a non-admin regardless of the UI.
          */}
          {isAdmin && (
            <>
              <Separator className="my-3 bg-sidebar-border" />
              <div className="flex items-center gap-1.5 px-3 pb-1 pt-1 text-2xs font-semibold uppercase tracking-wider text-sidebar-muted">
                <Shield className="size-3" />
                Administration
              </div>
              <NavSection items={ADMIN_NAV} onNavigate={onClose} />
            </>
          )}

          <Separator className="my-3 bg-sidebar-border" />
          <NavSection title="Settings" items={SETTINGS_NAV} onNavigate={onClose} />
        </nav>

        <div className="shrink-0 border-t border-sidebar-border px-4 py-3">
          <p className="text-2xs text-sidebar-muted">
            Every launch and sign-in is recorded in the portal audit log.
          </p>
        </div>
      </aside>
    </>
  );
}
