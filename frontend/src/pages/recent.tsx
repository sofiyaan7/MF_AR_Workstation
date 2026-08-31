import { Clock } from "lucide-react";
import { Link } from "react-router-dom";

import { ProjectCard } from "@/components/projects/project-card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/ui/states";
import { useRecentProjects } from "@/hooks/use-projects";

export function RecentPage() {
  const { data, isLoading, error, refetch } = useRecentProjects(30);

  return (
    <div>
      <PageHeader
        title="Recently Used"
        description="The projects you have opened most recently, newest first."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Recently Used" }]}
      />

      {isLoading && <CardGridSkeleton count={6} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && (data?.length ?? 0) === 0 && (
        <EmptyState
          icon={Clock}
          title="Nothing opened yet"
          description="Projects you launch from the portal are tracked here so you can get back to them quickly."
          action={
            <Button variant="outline" asChild>
              <Link to="/projects">Browse projects</Link>
            </Button>
          }
        />
      )}

      {!isLoading && !error && data && data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {data.map(({ project, last_opened_at }) => (
            <ProjectCard
              key={project.id}
              project={{ ...project, my_last_opened_at: last_opened_at }}
              showLastOpened
            />
          ))}
        </div>
      )}
    </div>
  );
}
