/** Typed wrappers around every API route the UI uses. */
import { api, unwrap } from "@/services/api";
import type {
  ActivityEntry, AnalyticsOverview, AnalyticsResponse, ApiMessage, CategoryDetail,
  DashboardResponse, LoginHistoryEntry, LoginResponse, MyActivityEntry, Page,
  ProjectAdminDetail, ProjectAdminRow, ProjectCard, ProjectDetail, ProjectFormValues,
  ProjectStatsResponse, Suggestion, SuggestionList, SuggestionStatus,
  RecentProject, TagRef, UserAdminView, UserProfile,
} from "@/types";

// --------------------------------------------------------------------------
// Auth
// --------------------------------------------------------------------------
export const authApi = {
  login: (username: string, password: string) =>
    unwrap<LoginResponse>(api.post("/auth/login", { username, password })),
  logout: () => unwrap<ApiMessage>(api.post("/auth/logout")),
  me: () => unwrap<UserProfile>(api.get("/auth/me")),
  updateProfile: (payload: {
    full_name?: string;
    employee_id?: string;
    email?: string;
    phone?: string;
  }) =>
    unwrap<UserProfile>(api.put("/auth/me", payload)),
  changePassword: (payload: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }) => unwrap<ApiMessage>(api.post("/auth/change-password", payload)),
  passwordPolicy: () =>
    unwrap<{ min_length: number; requirements: string[] }>(api.get("/auth/password-policy")),
  forgotPassword: (username: string) =>
    unwrap<ApiMessage>(api.post("/auth/forgot-password", { username })),
};

// --------------------------------------------------------------------------
// Projects (employee)
// --------------------------------------------------------------------------
export interface ProjectQuery {
  search?: string;
  category_id?: number;
  tag?: string[];
  owner?: string;
  status?: string;
  favourites_only?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
}

export const projectsApi = {
  list: (params: ProjectQuery = {}) =>
    unwrap<Page<ProjectCard>>(api.get("/projects", { params })),
  dashboard: () => unwrap<DashboardResponse>(api.get("/projects/dashboard")),
  recent: (limit = 20) =>
    unwrap<RecentProject[]>(api.get("/projects/recent", { params: { limit } })),
  favourites: () => unwrap<ProjectCard[]>(api.get("/projects/favourites")),
  categories: () => unwrap<CategoryDetail[]>(api.get("/projects/categories")),
  tags: () => unwrap<TagRef[]>(api.get("/projects/tags")),
  owners: () => unwrap<string[]>(api.get("/projects/owners")),
  detail: (id: number) => unwrap<ProjectDetail>(api.get(`/projects/${id}`)),
  open: (id: number) =>
    unwrap<{ project_id: number; url: string; open_in_new_tab: boolean; message: string }>(
      api.post(`/projects/${id}/open`),
    ),
  addFavourite: (id: number) => unwrap<ApiMessage>(api.post(`/projects/${id}/favourite`)),
  removeFavourite: (id: number) => unwrap<ApiMessage>(api.delete(`/projects/${id}/favourite`)),
};

// --------------------------------------------------------------------------
// Suggestions (per project, visible to everyone who can see the project)
// --------------------------------------------------------------------------
export const suggestionsApi = {
  list: (projectId: number, status?: SuggestionStatus) =>
    unwrap<SuggestionList>(
      api.get(`/projects/${projectId}/suggestions`, { params: status ? { status } : {} }),
    ),
  create: (projectId: number, payload: { title: string; body?: string | null }) =>
    unwrap<Suggestion>(api.post(`/projects/${projectId}/suggestions`, payload)),
  setStatus: (projectId: number, suggestionId: number, status: SuggestionStatus) =>
    unwrap<Suggestion>(
      api.patch(`/projects/${projectId}/suggestions/${suggestionId}`, { status }),
    ),
};

// --------------------------------------------------------------------------
// Activity (own)
// --------------------------------------------------------------------------
export const activityApi = {
  mine: (params: { limit?: number; offset?: number; event_type?: string[] } = {}) =>
    unwrap<Page<MyActivityEntry>>(api.get("/activity/me", { params })),
};

// --------------------------------------------------------------------------
// Admin — users
// --------------------------------------------------------------------------
export interface UserQuery {
  search?: string;
  department?: string;
  role?: string;
  status?: string;
  is_active?: boolean;
  include_deleted?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
}

export const adminUsersApi = {
  list: (params: UserQuery = {}) =>
    unwrap<Page<UserAdminView>>(api.get("/admin/users", { params })),
  departments: () => unwrap<string[]>(api.get("/admin/users/departments")),
  get: (id: number) => unwrap<UserAdminView>(api.get(`/admin/users/${id}`)),
  create: (payload: Record<string, unknown>) =>
    unwrap<{ user: UserAdminView; temporary_password: string | null }>(
      api.post("/admin/users", payload),
    ),
  update: (id: number, payload: Record<string, unknown>) =>
    unwrap<UserAdminView>(api.put(`/admin/users/${id}`, payload)),
  enable: (id: number) => unwrap<ApiMessage>(api.post(`/admin/users/${id}/enable`)),
  disable: (id: number) => unwrap<ApiMessage>(api.post(`/admin/users/${id}/disable`)),
  unlock: (id: number) => unwrap<ApiMessage>(api.post(`/admin/users/${id}/unlock`)),
  resetPassword: (id: number) =>
    unwrap<{ user_id: number; employee_id: string; temporary_password: string; message: string }>(
      api.post(`/admin/users/${id}/reset-password`),
    ),
  remove: (id: number) => unwrap<ApiMessage>(api.delete(`/admin/users/${id}`)),
  activity: (id: number, params: { limit?: number; offset?: number } = {}) =>
    unwrap<Page<ActivityEntry>>(api.get(`/admin/users/${id}/activity`, { params })),
  loginHistory: (id: number, params: { limit?: number; offset?: number } = {}) =>
    unwrap<Page<LoginHistoryEntry>>(api.get(`/admin/users/${id}/login-history`, { params })),
};

// --------------------------------------------------------------------------
// Admin — projects & categories
// --------------------------------------------------------------------------
export const adminProjectsApi = {
  list: (params: Record<string, unknown> = {}) =>
    unwrap<Page<ProjectAdminRow>>(api.get("/admin/projects", { params })),
  get: (id: number) => unwrap<ProjectAdminDetail>(api.get(`/admin/projects/${id}`)),
  create: (payload: ProjectFormValues) =>
    unwrap<ProjectAdminDetail>(api.post("/admin/projects", payload)),
  update: (id: number, payload: Partial<ProjectFormValues>) =>
    unwrap<ProjectAdminDetail>(api.put(`/admin/projects/${id}`, payload)),
  duplicate: (id: number) =>
    unwrap<ProjectAdminDetail>(api.post(`/admin/projects/${id}/duplicate`)),
  remove: (id: number) => unwrap<ApiMessage>(api.delete(`/admin/projects/${id}`)),
  restore: (id: number) => unwrap<ProjectAdminDetail>(api.post(`/admin/projects/${id}/restore`)),
  stats: (id: number, days = 30) =>
    unwrap<ProjectStatsResponse>(api.get(`/admin/projects/${id}/stats`, { params: { days } })),
};

export const adminCategoriesApi = {
  list: () => unwrap<CategoryDetail[]>(api.get("/admin/categories")),
  create: (payload: { name: string; description?: string; icon?: string; colour?: string; sort_order?: number }) =>
    unwrap<CategoryDetail>(api.post("/admin/categories", payload)),
  update: (id: number, payload: Record<string, unknown>) =>
    unwrap<CategoryDetail>(api.put(`/admin/categories/${id}`, payload)),
  remove: (id: number) => unwrap<ApiMessage>(api.delete(`/admin/categories/${id}`)),
};

// --------------------------------------------------------------------------
// Admin — activity & analytics
// --------------------------------------------------------------------------
export interface ActivityQuery {
  employee_id?: string;
  user_id?: number;
  event_type?: string[];
  project_id?: number;
  success?: boolean;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const adminActivityApi = {
  list: (params: ActivityQuery = {}) =>
    unwrap<Page<ActivityEntry>>(api.get("/admin/activity", { params })),
  eventTypes: () => unwrap<string[]>(api.get("/admin/activity/event-types")),
  loginAttempts: (params: { successful?: boolean; limit?: number; offset?: number } = {}) =>
    unwrap<Page<LoginHistoryEntry>>(api.get("/admin/login-attempts", { params })),
  overview: () => unwrap<AnalyticsOverview>(api.get("/admin/analytics/overview")),
  analytics: (days = 30) =>
    unwrap<AnalyticsResponse>(api.get("/admin/analytics", { params: { days } })),
  exportCsv: async (params: ActivityQuery = {}): Promise<Blob> => {
    const response = await api.get("/admin/activity/export", { params, responseType: "blob" });
    return response.data as Blob;
  },
};
