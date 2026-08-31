import { FolderOpen } from "lucide-react";

import { ProjectCard } from "@/components/projects/project-card";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/ui/states";
import type { ProjectCard as ProjectCardType } from "@/types";

interface ProjectGridProps {
  projects: ProjectCardType[] | undefined;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  showLastOpened?: boolean;
  skeletonCount?: number;
}

export function ProjectGrid({
  projects,
  isLoading,
  error,
  onRetry,
  emptyTitle = "No projects yet",
  emptyDescription = "Once an administrator adds a project, it appears here automatically.",
  emptyAction,
  showLastOpened,
  skeletonCount = 6,
}: ProjectGridProps) {
  if (isLoading) return <CardGridSkeleton count={skeletonCount} />;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (!projects || projects.length === 0) {
    return (
      <EmptyState
        icon={FolderOpen}
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
      />
    );
  }

  return (
    <div
      data-testid="project-grid"
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
    >
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} showLastOpened={showLastOpened} />
      ))}
    </div>
  );
}
