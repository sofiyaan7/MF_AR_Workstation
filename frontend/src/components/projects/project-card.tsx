import { ArrowUpRight, Clock, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ProjectIcon } from "@/components/ui/project-icon";
import { ProjectStatusBadge } from "@/components/ui/status-badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useOpenProject, useToggleFavourite } from "@/hooks/use-projects";
import type { ProjectCard as ProjectCardType } from "@/types";

interface ProjectCardProps {
  project: ProjectCardType;
  showLastOpened?: boolean;
  className?: string;
}

export function ProjectCard({ project, showLastOpened, className }: ProjectCardProps) {
  const openProject = useOpenProject();
  const toggleFavourite = useToggleFavourite();

  const launchable = project.status !== "COMING_SOON";
  const summary = project.short_description || project.description || "No description provided.";

  return (
    <Card
      className={cn(
        "group flex flex-col transition-shadow duration-150 hover:shadow-card-hover",
        className,
      )}
    >
      <div className="flex items-start gap-3 p-5 pb-3">
        <ProjectIcon icon={project.icon} colour={project.colour} seed={project.slug} />
        <div className="min-w-0 flex-1">
          <Link
            to={`/projects/${project.id}`}
            className="block rounded text-sm font-semibold leading-snug text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {project.name}
          </Link>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {project.category?.name ?? "Uncategorised"}
            {project.owner_name ? ` · ${project.owner_name}` : ""}
          </p>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(
                "shrink-0",
                project.is_favourite
                  ? "text-warning hover:text-warning"
                  : "text-muted-foreground opacity-0 focus-visible:opacity-100 group-hover:opacity-100",
              )}
              disabled={toggleFavourite.isPending}
              onClick={() => toggleFavourite.mutate({ project })}
              aria-label={project.is_favourite ? "Remove from favourites" : "Add to favourites"}
              aria-pressed={project.is_favourite}
            >
              <Star className={cn(project.is_favourite && "fill-current")} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {project.is_favourite ? "Remove from favourites" : "Add to favourites"}
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="flex-1 px-5">
        <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">{summary}</p>

        {project.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {project.tags.slice(0, 3).map((tag) => (
              <Badge key={tag.id} variant="secondary" className="text-2xs">
                {tag.name}
              </Badge>
            ))}
            {project.tags.length > 3 && (
              <Badge variant="outline" className="text-2xs">
                +{project.tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-border px-5 py-3">
        <ProjectStatusBadge status={project.status} />
        {showLastOpened && project.my_last_opened_at && (
          <span className="flex items-center gap-1 text-2xs text-muted-foreground">
            <Clock className="size-3" />
            {formatRelative(project.my_last_opened_at)}
          </span>
        )}
        <Button
          size="sm"
          className="ml-auto"
          disabled={!launchable || openProject.isPending}
          loading={openProject.isPending && openProject.variables?.id === project.id}
          onClick={() => openProject.mutate(project)}
        >
          {launchable ? "Open Project" : "Coming soon"}
          {launchable && <ArrowUpRight />}
        </Button>
      </div>
    </Card>
  );
}
