/** React Query hooks for the project catalogue, plus the launch/favourite actions. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api";
import { projectsApi, type ProjectQuery } from "@/services/endpoints";
import type { ProjectCard } from "@/types";

export const projectKeys = {
  all: ["projects"] as const,
  list: (query: ProjectQuery) => ["projects", "list", query] as const,
  dashboard: () => ["projects", "dashboard"] as const,
  detail: (id: number) => ["projects", "detail", id] as const,
  recent: () => ["projects", "recent"] as const,
  favourites: () => ["projects", "favourites"] as const,
  categories: () => ["projects", "categories"] as const,
  tags: () => ["projects", "tags"] as const,
  owners: () => ["projects", "owners"] as const,
};

export function useDashboard() {
  return useQuery({ queryKey: projectKeys.dashboard(), queryFn: projectsApi.dashboard });
}

export function useProjectList(query: ProjectQuery) {
  return useQuery({
    queryKey: projectKeys.list(query),
    queryFn: () => projectsApi.list(query),
    placeholderData: (previous) => previous, // keeps the grid stable while typing
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => projectsApi.detail(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useRecentProjects(limit = 20) {
  return useQuery({ queryKey: [...projectKeys.recent(), limit], queryFn: () => projectsApi.recent(limit) });
}

export function useFavouriteProjects() {
  return useQuery({ queryKey: projectKeys.favourites(), queryFn: projectsApi.favourites });
}

export function useCategories() {
  return useQuery({ queryKey: projectKeys.categories(), queryFn: projectsApi.categories });
}

export function useProjectTags() {
  return useQuery({ queryKey: projectKeys.tags(), queryFn: projectsApi.tags });
}

export function useProjectOwners() {
  return useQuery({ queryKey: projectKeys.owners(), queryFn: projectsApi.owners });
}

/**
 * Records the launch server-side, then navigates.
 *
 * The window is opened synchronously *before* awaiting so the browser still
 * attributes it to the click and does not block it as a popup.
 *
 * "noopener" must NOT go in the features string: window.open() returns null
 * whenever it is present, which would throw away the handle needed to point
 * the tab at the project. Clearing `opener` on the handle below gives the
 * same protection while keeping the reference.
 */
export function useOpenProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (project: Pick<ProjectCard, "id" | "name" | "open_in_new_tab">) => {
      const newTab = project.open_in_new_tab ? window.open("", "_blank") : null;
      // Cut the opener link immediately so the blank tab can never reach back
      // into this window, even if the request below is slow or fails.
      if (newTab) newTab.opener = null;
      try {
        const result = await projectsApi.open(project.id);
        if (newTab) {
          newTab.location.replace(result.url);
        } else {
          window.location.assign(result.url);
        }
        return result;
      } catch (error) {
        newTab?.close();
        throw error;
      }
    },
    onSuccess: (result) => {
      toast.success(result.message);
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Could not open that project.");
    },
  });
}

export function useToggleFavourite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ project }: { project: Pick<ProjectCard, "id" | "name" | "is_favourite"> }) =>
      project.is_favourite
        ? projectsApi.removeFavourite(project.id)
        : projectsApi.addFavourite(project.id),
    onSuccess: (response) => {
      toast.success(response.message);
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Could not update your favourites.");
    },
  });
}
