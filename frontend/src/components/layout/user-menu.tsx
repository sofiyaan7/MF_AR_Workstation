import { Activity, ChevronDown, LogOut, Monitor, Moon, Settings, ShieldCheck, Sun } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";
import { useTheme } from "@/hooks/use-theme";
import { initials } from "@/lib/utils";

export function UserMenu() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = React.useState(false);

  if (!user) return null;

  const handleLogout = async () => {
    setSigningOut(true);
    await logout();
    toast.success("You have been signed out");
    navigate("/login", { replace: true });
  };

  const nextTheme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  const themeLabel = theme === "light" ? "Light" : theme === "dark" ? "Dark" : "System";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-2 rounded-md py-1 pl-1 pr-2 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
            aria-hidden
          >
            {initials(user.full_name)}
          </span>
          <span className="hidden min-w-0 leading-tight sm:block">
            <span className="block truncate text-sm font-medium text-foreground">{user.full_name}</span>
            <span className="block truncate text-2xs text-muted-foreground">{user.employee_id}</span>
          </span>
          <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal">
          <p className="text-sm font-semibold text-foreground">{user.full_name}</p>
          <p className="text-xs text-muted-foreground">Employee ID: {user.employee_id}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/profile")}>
          <Settings />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/activity")}>
          <Activity />
          My Activity
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate("/security")}>
          <ShieldCheck />
          Security
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={(event) => {
            event.preventDefault();
            setTheme(nextTheme);
          }}
        >
          <ThemeIcon />
          Theme: {themeLabel}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem destructive disabled={signingOut} onSelect={handleLogout}>
          <LogOut />
          {signingOut ? "Signing out…" : "Logout"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
