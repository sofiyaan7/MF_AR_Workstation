import { ExternalLink, Github, Pencil, Star, TrendingUp, Users } from "lucide-react";
import * as React from "react";
import { useParams } from "react-router-dom";

import { BarList, TrendChart } from "@/components/admin/charts";
import { ProjectFormDialog } from "@/components/admin/project-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { ProjectIcon } from "@/components/ui/project-icon";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState, StatsSkeleton } from "@/components/ui/states";
import { ProjectStatusBadge, VisibilityBadge } from "@/components/ui/status-badge";
import { useAdminProject, useProjectStats } from "@/hooks/use-admin";
import { formatDateTime, formatRelative } from "@/lib/format";

const PERIODS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
];

export function AdminProjectDetailPage() {
  const { projectId } = useParams();
  const id = Number(projectId);

  const [days, setDays] = React.useState("30");
  const [formOpen, setFormOpen] = React.useState(false);

  const { data: project, isLoading, error, refetch } = useAdminProject(id);
  const { data: stats, isLoading: statsLoading } = useProjectStats(id, Number(days));

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-72" />
        <StatsSkeleton count={4} />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error || !project) {
    return <ErrorState error={error ?? new Error("Project not found")} onRetry={() => refetch()} />;
  }

  return (
    <div>
      <PageHeader
        title={project.name}
        description="Usage analytics and configuration for this project."
        breadcrumbs={[
          { label: "Home", to: "/" },
          { label: "Admin" },
          { label: "Projects", to: "/admin/projects" },
          { label: project.name },
        ]}
        actions={
          <>
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger className="w-40" aria-label="Reporting period">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PERIODS.map((period) => (
                  <SelectItem key={period.value} value={period.value}>
                    {period.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => setFormOpen(true)}>
              <Pencil />
              Edit project
            </Button>
          </>
        }
      />

      <Card className="mb-6">
        <CardHeader className="flex-row items-start gap-4 space-y-0">
          <ProjectIcon icon={project.icon} colour={project.colour} seed={project.slug} size="lg" />
          <div className="min-w-0 flex-1">
            <CardTitle className="text-base">{project.name}</CardTitle>
            <CardDescription className="mt-1">
              {project.short_description || project.description || "No description provided."}
            </CardDescription>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <ProjectStatusBadge status={project.status} />
              <VisibilityBadge visibility={project.visibility} />
              {project.category && <Badge variant="secondary">{project.category.name}</Badge>}
              {project.is_featured && <Badge variant="default">Featured</Badge>}
              {!project.is_active && <Badge variant="muted">Disabled</Badge>}
            </div>
            <div className="mt-3 grid gap-x-6 gap-y-1 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
              <p>Owner: <span className="text-foreground">{project.owner_name ?? "—"}</span></p>
              <p>Created: <span className="text-foreground">{formatDateTime(project.created_at)}</span></p>
              <p>Updated: <span className="text-foreground">{formatDateTime(project.updated_at)}</span></p>
              <p>
                Last opened:{" "}
                <span className="text-foreground">
                  {project.last_opened_at ? formatRelative(project.last_opened_at) : "Never"}
                </span>
              </p>
            </div>
            <div className="mt-3 flex flex-col gap-1.5">
              <a
                href={project.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded font-mono text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ExternalLink className="size-3" />
                {project.url}
              </a>
              {project.repository_url && (
                <a
                  href={project.repository_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Open the ${project.name} repository`}
                  className="inline-flex items-center gap-1.5 rounded font-mono text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Github className="size-3" />
                  {project.repository_url}
                </a>
              )}
            </div>
          </div>
        </CardHeader>
        {project.allowed_employee_ids.length > 0 && (
          <CardContent className="pt-0">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Permitted employees ({project.allowed_employee_ids.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {project.allowed_employee_ids.map((employeeId) => (
                <Badge key={employeeId} variant="secondary" className="font-mono">
                  {employeeId}
                </Badge>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {statsLoading ? (
        <StatsSkeleton count={4} />
      ) : (
        stats && (
          <>
            <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Total opens" value={stats.total_opens} icon={TrendingUp} />
              <StatCard label="Unique users" value={stats.unique_users} icon={Users} />
              <StatCard
                label={`Opens in ${days} days`}
                value={stats.opens_in_period}
                icon={TrendingUp}
              />
              <StatCard label="Favourited by" value={stats.favourite_count} icon={Star} />
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Opens over time</CardTitle>
                  <CardDescription>
                    Daily launches over the {days === "7" ? "last week" : `last ${days} days`}.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TrendChart data={stats.daily_opens} valueLabel="opens" colourIndex={2} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Most active users</CardTitle>
                  <CardDescription>All-time, for this project.</CardDescription>
                </CardHeader>
                <CardContent>
                  <BarList
                    items={stats.top_users.map((user) => ({
                      label: user.full_name,
                      value: user.opens,
                      hint: user.employee_id,
                    }))}
                  />
                </CardContent>
              </Card>
            </div>
          </>
        )
      )}

      <ProjectFormDialog open={formOpen} onOpenChange={setFormOpen} project={project} />
    </div>
  );
}
