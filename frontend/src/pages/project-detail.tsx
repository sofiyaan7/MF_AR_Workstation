import {
  ArrowUpRight, BookOpen, Calendar, Clock, ExternalLink, Eye, RefreshCcw, Star, User,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SuggestionBox } from "@/components/suggestions/suggestion-box";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { ProjectIcon } from "@/components/ui/project-icon";
import { Separator } from "@/components/ui/separator";
import { ErrorState } from "@/components/ui/states";
import { ProjectStatusBadge, VisibilityBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useOpenProject, useProject, useToggleFavourite } from "@/hooks/use-projects";
import { formatDateTime, formatNumber, formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

function DetailRow({ icon: Icon, label, value }: { icon: typeof User; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="text-sm font-medium text-foreground">{value}</div>
      </div>
    </div>
  );
}

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const id = Number(projectId);

  const { data: project, isLoading, error, refetch } = useProject(id);
  const openProject = useOpenProject();
  const toggleFavourite = useToggleFavourite();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <ErrorState
        error={error ?? new Error("Project not found")}
        onRetry={() => refetch()}
      />
    );
  }

  const launchable = project.status !== "COMING_SOON";

  return (
    <div>
      <PageHeader
        title={project.name}
        breadcrumbs={[
          { label: "Home", to: "/" },
          { label: "Projects", to: "/projects" },
          { label: project.name },
        ]}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => toggleFavourite.mutate({ project })}
              disabled={toggleFavourite.isPending}
              aria-pressed={project.is_favourite}
            >
              <Star className={cn(project.is_favourite && "fill-warning text-warning")} />
              {project.is_favourite ? "Favourited" : "Favourite"}
            </Button>
            <Button
              onClick={() => openProject.mutate(project)}
              disabled={!launchable}
              loading={openProject.isPending}
            >
              {launchable ? "Open Project" : "Coming soon"}
              {launchable && <ArrowUpRight />}
            </Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="flex-row items-start gap-4 space-y-0">
              <ProjectIcon icon={project.icon} colour={project.colour} seed={project.slug} size="lg" />
              <div className="min-w-0 flex-1">
                <CardTitle className="text-lg">{project.name}</CardTitle>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <ProjectStatusBadge status={project.status} />
                  {project.category && <Badge variant="secondary">{project.category.name}</Badge>}
                  {project.is_featured && <Badge variant="default">Featured</Badge>}
                  {isAdmin && <VisibilityBadge visibility={project.visibility} />}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                {project.description || project.short_description || "No description provided."}
              </p>

              {project.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {project.tags.map((tag) => (
                    <Badge key={tag.id} variant="outline">
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              )}

              <Separator />

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  onClick={() => openProject.mutate(project)}
                  disabled={!launchable}
                  loading={openProject.isPending}
                >
                  {launchable ? "Open Project" : "Coming soon"}
                  {launchable && <ArrowUpRight />}
                </Button>
                {project.documentation_url && (
                  <Button variant="outline" asChild>
                    <a href={project.documentation_url} target="_blank" rel="noopener noreferrer">
                      <BookOpen />
                      Documentation
                    </a>
                  </Button>
                )}
                <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                  <ExternalLink className="size-3 shrink-0" />
                  <span className="truncate font-mono">{project.url}</span>
                </span>
              </div>

              {project.open_in_new_tab && launchable && (
                <p className="text-xs text-muted-foreground">
                  This project opens in a new browser tab.
                </p>
              )}
            </CardContent>
          </Card>

          {isAdmin && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Administration</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => navigate(`/admin/projects/${project.id}`)}>
                  View usage analytics
                </Button>
                <Button variant="outline" size="sm" onClick={() => navigate("/admin/projects")}>
                  Manage projects
                </Button>
              </CardContent>
            </Card>
          )}

          <SuggestionBox projectId={project.id} />
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Details</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border pt-0">
              <DetailRow icon={User} label="Owner" value={project.owner_name || "Not assigned"} />
              <DetailRow
                icon={Calendar}
                label="Created"
                value={formatDateTime(project.created_at)}
              />
              <DetailRow
                icon={RefreshCcw}
                label="Last updated"
                value={formatDateTime(project.updated_at)}
              />
              <DetailRow
                icon={Clock}
                label="Last opened"
                value={project.last_opened_at ? formatRelative(project.last_opened_at) : "Never"}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Usage</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-2xl font-semibold tabular-nums text-foreground">
                    {formatNumber(project.total_opens)}
                  </p>
                  <p className="text-xs text-muted-foreground">Total opens</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold tabular-nums text-foreground">
                    {formatNumber(project.unique_users)}
                  </p>
                  <p className="text-xs text-muted-foreground">Unique users</p>
                </div>
              </div>
              <Separator className="my-4" />
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Eye className="size-4" />
                You have opened this {formatNumber(project.my_open_count)} time
                {project.my_open_count === 1 ? "" : "s"}
                {project.my_last_opened_at && ` · last ${formatRelative(project.my_last_opened_at)}`}
              </div>
            </CardContent>
          </Card>

          {isAdmin && project.allowed_employee_ids.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Permitted employees</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-1.5 pt-0">
                {project.allowed_employee_ids.map((employeeId) => (
                  <Badge key={employeeId} variant="secondary" className="font-mono">
                    {employeeId}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
