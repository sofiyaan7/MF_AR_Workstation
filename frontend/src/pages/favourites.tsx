import { Star } from "lucide-react";
import { Link } from "react-router-dom";

import { ProjectGrid } from "@/components/projects/project-grid";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { useFavouriteProjects } from "@/hooks/use-projects";

export function FavouritesPage() {
  const { data, isLoading, error, refetch } = useFavouriteProjects();

  return (
    <div>
      <PageHeader
        title="My Favourites"
        description="Projects you have starred, kept private to your account."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "My Favourites" }]}
        actions={
          !isLoading && data ? (
            <span className="text-sm text-muted-foreground">
              {data.length} favourite{data.length === 1 ? "" : "s"}
            </span>
          ) : null
        }
      />
      <ProjectGrid
        projects={data}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        emptyTitle="No favourites yet"
        emptyDescription="Star a project from the dashboard or its detail page and it will be pinned here."
        emptyAction={
          <Button variant="outline" asChild>
            <Link to="/projects">
              <Star />
              Browse projects
            </Link>
          </Button>
        }
      />
    </div>
  );
}
