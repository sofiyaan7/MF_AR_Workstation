/** React Query hooks for the administrator areas. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api";
import {
  activityApi, adminActivityApi, adminCategoriesApi, adminProjectsApi, adminUsersApi,
  type ActivityQuery, type UserQuery,
} from "@/services/endpoints";
import type { ProjectFormValues } from "@/types";

export const adminKeys = {
  users: (query: UserQuery) => ["admin", "users", query] as const,
  usersAll: ["admin", "users"] as const,
  user: (id: number) => ["admin", "user", id] as const,
  userActivity: (id: number) => ["admin", "user", id, "activity"] as const,
  userLogins: (id: number) => ["admin", "user", id, "logins"] as const,
  departments: ["admin", "departments"] as const,
  projects: (query: Record<string, unknown>) => ["admin", "projects", query] as const,
  projectsAll: ["admin", "projects"] as const,
  project: (id: number) => ["admin", "project", id] as const,
  projectStats: (id: number, days: number) => ["admin", "project", id, "stats", days] as const,
  categories: ["admin", "categories"] as const,
  activity: (query: ActivityQuery) => ["admin", "activity", query] as const,
  activityAll: ["admin", "activity"] as const,
  eventTypes: ["admin", "event-types"] as const,
  analytics: (days: number) => ["admin", "analytics", days] as const,
  overview: ["admin", "overview"] as const,
};

function reportError(fallback: string) {
  return (error: unknown) => {
    if (error instanceof ApiError) {
      toast.error(error.message, {
        description: error.details.length ? error.details.join(" · ") : undefined,
      });
    } else {
      toast.error(fallback);
    }
  };
}

// --------------------------------------------------------------------------
// Users
// --------------------------------------------------------------------------
export function useAdminUsers(query: UserQuery) {
  return useQuery({
    queryKey: adminKeys.users(query),
    queryFn: () => adminUsersApi.list(query),
    placeholderData: (previous) => previous,
  });
}

export function useDepartments() {
  return useQuery({ queryKey: adminKeys.departments, queryFn: adminUsersApi.departments });
}

export function useUserActivity(id: number) {
  return useQuery({
    queryKey: adminKeys.userActivity(id),
    queryFn: () => adminUsersApi.activity(id, { limit: 100 }),
    enabled: id > 0,
  });
}

export function useUserLoginHistory(id: number) {
  return useQuery({
    queryKey: adminKeys.userLogins(id),
    queryFn: () => adminUsersApi.loginHistory(id, { limit: 50 }),
    enabled: id > 0,
  });
}

export function useUserMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.usersAll });
    queryClient.invalidateQueries({ queryKey: adminKeys.overview });
  };

  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) => adminUsersApi.create(payload),
    onSuccess: (result) => {
      toast.success(`${result.user.full_name} can now sign in`, {
        description: `Employee ID ${result.user.employee_id}`,
      });
      invalidate();
    },
    onError: reportError("Could not create that employee."),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      adminUsersApi.update(id, payload),
    onSuccess: (user) => {
      toast.success(`${user.full_name} updated`);
      invalidate();
    },
    onError: reportError("Could not update that employee."),
  });

  const setEnabled = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      enabled ? adminUsersApi.enable(id) : adminUsersApi.disable(id),
    onSuccess: (response) => {
      toast.success(response.message);
      invalidate();
    },
    onError: reportError("Could not change that account's status."),
  });

  const unlock = useMutation({
    mutationFn: (id: number) => adminUsersApi.unlock(id),
    onSuccess: (response) => {
      toast.success(response.message);
      invalidate();
    },
    onError: reportError("Could not unlock that account."),
  });

  const resetPassword = useMutation({
    mutationFn: (id: number) => adminUsersApi.resetPassword(id),
    onSuccess: () => invalidate(),
    onError: reportError("Could not reset that password."),
  });

  const remove = useMutation({
    mutationFn: (id: number) => adminUsersApi.remove(id),
    onSuccess: (response) => {
      toast.success(response.message, { description: response.detail ?? undefined });
      invalidate();
    },
    onError: reportError("Could not remove that employee."),
  });

  return { create, update, setEnabled, unlock, resetPassword, remove };
}

// --------------------------------------------------------------------------
// Projects
// --------------------------------------------------------------------------
export function useAdminProjects(query: Record<string, unknown>) {
  return useQuery({
    queryKey: adminKeys.projects(query),
    queryFn: () => adminProjectsApi.list(query),
    placeholderData: (previous) => previous,
  });
}

export function useAdminProject(id: number) {
  return useQuery({
    queryKey: adminKeys.project(id),
    queryFn: () => adminProjectsApi.get(id),
    enabled: id > 0,
  });
}

export function useProjectStats(id: number, days: number) {
  return useQuery({
    queryKey: adminKeys.projectStats(id, days),
    queryFn: () => adminProjectsApi.stats(id, days),
    enabled: id > 0,
  });
}

export function useProjectMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.projectsAll });
    queryClient.invalidateQueries({ queryKey: ["projects"] });
    queryClient.invalidateQueries({ queryKey: adminKeys.overview });
  };

  const create = useMutation({
    mutationFn: (payload: ProjectFormValues) => adminProjectsApi.create(payload),
    onSuccess: (project) => {
      toast.success(`'${project.name}' added`, {
        description: "It is now on the dashboard for everyone who can see it.",
      });
      invalidate();
    },
    onError: reportError("Could not add that project."),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<ProjectFormValues> }) =>
      adminProjectsApi.update(id, payload),
    onSuccess: (project) => {
      toast.success(`'${project.name}' updated`);
      invalidate();
    },
    onError: reportError("Could not update that project."),
  });

  const duplicate = useMutation({
    mutationFn: (id: number) => adminProjectsApi.duplicate(id),
    onSuccess: (project) => {
      toast.success(`Created '${project.name}'`, { description: "The copy starts disabled." });
      invalidate();
    },
    onError: reportError("Could not duplicate that project."),
  });

  const remove = useMutation({
    mutationFn: (id: number) => adminProjectsApi.remove(id),
    onSuccess: (response) => {
      toast.success(response.message, { description: response.detail ?? undefined });
      invalidate();
    },
    onError: reportError("Could not delete that project."),
  });

  const restore = useMutation({
    mutationFn: (id: number) => adminProjectsApi.restore(id),
    onSuccess: (project) => {
      toast.success(`'${project.name}' restored`);
      invalidate();
    },
    onError: reportError("Could not restore that project."),
  });

  return { create, update, duplicate, remove, restore };
}

// --------------------------------------------------------------------------
// Categories
// --------------------------------------------------------------------------
export function useAdminCategories() {
  return useQuery({ queryKey: adminKeys.categories, queryFn: adminCategoriesApi.list });
}

export function useCategoryMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.categories });
    queryClient.invalidateQueries({ queryKey: ["projects"] });
  };

  const create = useMutation({
    mutationFn: (payload: { name: string; description?: string; icon?: string; colour?: string }) =>
      adminCategoriesApi.create(payload),
    onSuccess: (category) => {
      toast.success(`Category '${category.name}' created`);
      invalidate();
    },
    onError: reportError("Could not create that category."),
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      adminCategoriesApi.update(id, payload),
    onSuccess: (category) => {
      toast.success(`Category '${category.name}' updated`);
      invalidate();
    },
    onError: reportError("Could not update that category."),
  });

  const remove = useMutation({
    mutationFn: (id: number) => adminCategoriesApi.remove(id),
    onSuccess: (response) => {
      toast.success(response.message);
      invalidate();
    },
    onError: reportError("Could not delete that category."),
  });

  return { create, update, remove };
}

// --------------------------------------------------------------------------
// Activity & analytics
// --------------------------------------------------------------------------
export function useAdminActivity(query: ActivityQuery) {
  return useQuery({
    queryKey: adminKeys.activity(query),
    queryFn: () => adminActivityApi.list(query),
    placeholderData: (previous) => previous,
  });
}

export function useEventTypes() {
  return useQuery({ queryKey: adminKeys.eventTypes, queryFn: adminActivityApi.eventTypes });
}

export function useAnalytics(days: number) {
  return useQuery({ queryKey: adminKeys.analytics(days), queryFn: () => adminActivityApi.analytics(days) });
}

export function useAnalyticsOverview() {
  return useQuery({ queryKey: adminKeys.overview, queryFn: adminActivityApi.overview });
}

export function useMyActivity(params: { limit?: number; offset?: number } = {}) {
  return useQuery({
    queryKey: ["activity", "me", params],
    queryFn: () => activityApi.mine(params),
    placeholderData: (previous) => previous,
  });
}
