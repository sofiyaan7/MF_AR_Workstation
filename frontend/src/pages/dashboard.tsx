import { Clock, FolderKanban, Plus, Sparkles, Star, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

import { ProjectCard } from "@/components/projects/project-card";
import { ProjectGrid } from "@/components/projects/project-grid";
import { Button } from "@/components/ui/button";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/ui/states";
import { useAuth } from "@/hooks/use-auth";
import { useDashboard } from "@/hooks/use-projects";
import { formatRelative } from "@/lib/format";
import { firstName } from "@/lib/utils";

function Section({
  title,
  icon: Icon,
  action,
  children,
}: {
  title: string;
  icon: typeof Star;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          <Icon className="size-4" />
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function DashboardPage() {
  const { user, isAdmin } = useAuth();
  const { data, isLoading, error, refetch } = useDashboard();

  const hasAnyProject = (data?.total_projects ?? 0) > 0;

  return (
    <div>
      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Welcome back, {user ? firstName(user.full_name) : "there"} 👋
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasAnyProject
              ? `You have access to ${data?.total_projects} project${data?.total_projects === 1 ? "" : "s"}.`
              : "Your project catalogue will appear here."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to="/projects">
              <FolderKanban />
              Browse all projects
            </Link>
          </Button>
          {isAdmin && (
            <Button size="sm" asChild>
              <Link to="/admin/projects?new=1">
                <Plus />
                Add project
              </Link>
            </Button>
          )}
        </div>
      </div>

      {error && <ErrorState error={error} onRetry={() => refetch()} className="mb-8" />}

      {isLoading && <CardGridSkeleton count={8} />}

      {!isLoading && !error && data && (
        <>
          {!hasAnyProject && (
            <EmptyState
              icon={FolderKanban}
              title="No projects available yet"
              description={
                isAdmin
                  ? "Add your first project from the admin panel — it appears here immediately, with no code changes."
                  : "Once an administrator grants you access to a project, it will appear here."
              }
              action={
                isAdmin ? (
                  <Button asChild>
                    <Link to="/admin/projects?new=1">
                      <Plus />
                      Add your first project
                    </Link>
                  </Button>
                ) : undefined
              }
            />
          )}

          {data.recent_projects.length > 0 && (
            <Section
              title="Recently opened"
              icon={Clock}
              action={
                <Button variant="link" size="sm" asChild className="h-auto p-0">
                  <Link to="/recent">View all</Link>
                </Button>
              }
            >
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {data.recent_projects.map(({ project, last_opened_at }) => (
                  <div key={project.id} className="relative">
                    <ProjectCard
                      project={{ ...project, my_last_opened_at: last_opened_at }}
                      showLastOpened
                    />
                  </div>
                ))}
              </div>
            </Section>
          )}

          {data.favourites.length > 0 && (
            <Section
              title="Favourite projects"
              icon={Star}
              action={
                <Button variant="link" size="sm" asChild className="h-auto p-0">
                  <Link to="/favourites">View all</Link>
                </Button>
              }
            >
              <ProjectGrid projects={data.favourites.slice(0, 4)} />
            </Section>
          )}

          {data.featured.length > 0 && (
            <Section title="Featured" icon={Sparkles}>
              <ProjectGrid projects={data.featured} />
            </Section>
          )}

          {data.recently_added.length > 0 && (
            <Section
              title="Recently added"
              icon={TrendingUp}
              action={
                <span className="text-xs text-muted-foreground">
                  Newest: {formatRelative(data.recently_added[0]?.created_at)}
                </span>
              }
            >
              <ProjectGrid projects={data.recently_added} />
            </Section>
          )}
        </>
      )}
    </div>
  );
}
