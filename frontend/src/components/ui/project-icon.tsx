import {
  AlertTriangle, BarChart3, Boxes, Briefcase, Calculator, Calendar, ClipboardList,
  Compass, Database, FileSpreadsheet, FileText, Gauge, Globe, Landmark, LayoutDashboard,
  LineChart, Microscope, Notebook, PieChart, RefreshCw, Rocket, Settings2, ShieldCheck,
  Table2, Target, TrendingUp, Users, Workflow, Wrench, Zap, type LucideIcon,
} from "lucide-react";

import { accentFor, cn, hexToRgba } from "@/lib/utils";

/**
 * Icons an administrator can choose from, keyed by the name stored in the
 * database. This is an explicit registry rather than a namespace import so the
 * bundle only carries the icons the portal actually offers.
 */
export const ICON_REGISTRY: Record<string, LucideIcon> = {
  AlertTriangle, BarChart3, Boxes, Briefcase, Calculator, Calendar, ClipboardList,
  Compass, Database, FileSpreadsheet, FileText, Gauge, Globe, Landmark, LayoutDashboard,
  LineChart, Microscope, Notebook, PieChart, RefreshCw, Rocket, Settings2, ShieldCheck,
  Table2, Target, TrendingUp, Users, Workflow, Wrench, Zap,
};

export const ICON_NAMES = Object.keys(ICON_REGISTRY);

/** Resolves a stored icon name, falling back to a neutral icon if unknown. */
export function resolveIcon(name: string | null | undefined): LucideIcon {
  if (!name) return LayoutDashboard;
  return ICON_REGISTRY[name] ?? LayoutDashboard;
}

interface ProjectIconProps {
  icon: string | null | undefined;
  colour?: string | null;
  seed: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = {
  sm: { box: "size-8 rounded-md", glyph: "size-4" },
  md: { box: "size-10 rounded-lg", glyph: "size-5" },
  lg: { box: "size-14 rounded-lg", glyph: "size-7" },
} as const;

export function ProjectIcon({ icon, colour, seed, size = "md", className }: ProjectIconProps) {
  const Icon = resolveIcon(icon);
  const accent = colour || accentFor(seed);
  const { box, glyph } = SIZES[size];

  return (
    <div
      className={cn("flex shrink-0 items-center justify-center", box, className)}
      style={{ backgroundColor: hexToRgba(accent, 0.12), color: accent }}
      aria-hidden
    >
      <Icon className={glyph} strokeWidth={1.9} />
    </div>
  );
}
