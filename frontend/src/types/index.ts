/** Shared API types. These mirror the FastAPI Pydantic schemas exactly. */

export type Role = "SUPER_ADMIN" | "ADMIN" | "USER";
export type AccountStatus = "ACTIVE" | "DISABLED" | "LOCKED" | "PENDING_PASSWORD_CHANGE";
export type ProjectStatus = "ACTIVE" | "MAINTENANCE" | "DEPRECATED" | "COMING_SOON";
export type Visibility = "ALL_EMPLOYEES" | "SPECIFIC_EMPLOYEES" | "ADMIN_ONLY";

export interface UserProfile {
  id: number;
  employee_id: string;
  full_name: string;
  email: string;
  department: string | null;
  job_title: string | null;
  role: Role;
  status: AccountStatus;
  is_admin: boolean;
  must_change_password: boolean;
  created_at: string;
  last_login_at: string | null;
  last_activity_at: string | null;
  password_changed_at: string | null;
  login_count: number;
}

export interface UserAdminView {
  id: number;
  employee_id: string;
  full_name: string;
  email: string;
  department: string | null;
  job_title: string | null;
  phone: string | null;
  role: Role;
  status: AccountStatus;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  last_activity_at: string | null;
  login_count: number;
  failed_login_attempts: number;
  locked_until: string | null;
  password_changed_at: string | null;
  must_change_password: boolean;
  created_by_id: number | null;
  notes: string | null;
}

export interface CategoryRef {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  colour: string | null;
}

export interface CategoryDetail extends CategoryRef {
  description: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  project_count: number;
}

export interface TagRef {
  id: number;
  name: string;
  slug: string;
}

export interface ProjectCard {
  id: number;
  name: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  url: string;
  icon: string;
  colour: string | null;
  status: ProjectStatus;
  visibility: Visibility;
  owner_name: string | null;
  is_featured: boolean;
  open_in_new_tab: boolean;
  total_opens: number;
  created_at: string;
  updated_at: string;
  last_opened_at: string | null;
  category: CategoryRef | null;
  tags: TagRef[];
  is_favourite: boolean;
  my_open_count: number;
  my_last_opened_at: string | null;
}

export interface ProjectDetail extends ProjectCard {
  documentation_url: string | null;
  sort_order: number;
  is_active: boolean;
  created_by_id: number | null;
  updated_by_id: number | null;
  unique_users: number;
  allowed_employee_ids: string[];
  allowed_departments: string[];
}

export interface ProjectAdminRow extends ProjectCard {
  is_active: boolean;
  is_deleted: boolean;
  unique_users: number;
  sort_order: number;
  repository_url: string | null;
}

/** ProjectDetail plus admin-only fields; the employee route returns ProjectDetail. */
export interface ProjectAdminDetail extends ProjectDetail {
  repository_url: string | null;
}

export interface RecentProject {
  project: ProjectCard;
  last_opened_at: string;
}

export interface DashboardResponse {
  featured: ProjectCard[];
  recent_projects: RecentProject[];
  favourites: ProjectCard[];
  recently_added: ProjectCard[];
  categories: CategoryDetail[];
  total_projects: number;
}

export interface ActivityEntry {
  id: number;
  user_id: number | null;
  employee_id: string | null;
  user_name: string | null;
  event_type: string;
  description: string | null;
  project_id: number | null;
  project_name: string | null;
  timestamp: string;
  ip_address: string | null;
  browser: string | null;
  os: string | null;
  device: string | null;
  success: boolean;
  event_metadata: Record<string, unknown> | null;
}

export interface MyActivityEntry {
  id: number;
  event_type: string;
  description: string | null;
  project_id: number | null;
  project_name: string | null;
  timestamp: string;
  ip_address: string | null;
  browser: string | null;
  device: string | null;
  success: boolean;
}

export interface LoginHistoryEntry {
  id: number;
  employee_id: string;
  successful: boolean;
  failure_reason: string | null;
  ip_address: string | null;
  user_agent: string | null;
  attempted_at: string;
}

export interface AnalyticsOverview {
  total_users: number;
  active_users: number;
  total_projects: number;
  active_projects: number;
  projects_added_this_month: number;
  logins_today: number;
  unique_active_users_today: number;
  project_opens_today: number;
  total_project_opens: number;
  failed_logins_today: number;
  activities_today: number;
  locked_accounts: number;
  most_viewed_project: { id: number; name: string; opens: number } | null;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface AnalyticsResponse {
  overview: AnalyticsOverview;
  daily_active_users: TimeSeriesPoint[];
  daily_logins: TimeSeriesPoint[];
  daily_project_opens: TimeSeriesPoint[];
  project_usage: { project_id: number; project_name: string; opens: number; unique_users: number }[];
  category_breakdown: { category: string; projects: number; opens: number }[];
  top_users: { user_id: number; employee_id: string; full_name: string; department: string | null; opens: number }[];
  login_trends: {
    successful_today: number;
    successful_week: number;
    successful_month: number;
    failed_today: number;
    failed_week: number;
    failed_month: number;
  };
}

export interface ProjectStatsResponse {
  project_id: number;
  total_opens: number;
  unique_users: number;
  opens_in_period: number;
  favourite_count: number;
  last_opened_at: string | null;
  daily_opens: TimeSeriesPoint[];
  top_users: { employee_id: string; full_name: string; opens: number }[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiMessage {
  message: string;
  detail?: string | null;
}

export interface LoginResponse {
  user: UserProfile;
  csrf_token: string;
  must_change_password: boolean;
  message: string;
}

export interface ProjectFormValues {
  name: string;
  url: string;
  description?: string | null;
  short_description?: string | null;
  documentation_url?: string | null;
  repository_url?: string | null;
  category_id?: number | null;
  tags: string[];
  owner_name?: string | null;
  icon: string;
  status: ProjectStatus;
  visibility: Visibility;
  allowed_employee_ids: string[];
  allowed_departments: string[];
  is_featured: boolean;
  open_in_new_tab: boolean;
  sort_order: number;
  is_active: boolean;
}

// --------------------------------------------------------------------------
// Suggestions
// --------------------------------------------------------------------------
export type SuggestionStatus = "OPEN" | "CLOSED";

export interface SuggestionAuthor {
  id: number;
  employee_id: string;
  full_name: string;
}

export interface Suggestion {
  id: number;
  project_id: number;
  title: string;
  body: string | null;
  status: SuggestionStatus;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  /** Null once the account that raised it has been deleted. */
  user: SuggestionAuthor | null;
  closed_by: SuggestionAuthor | null;
  /** Whether the signed-in user may close or reopen this one. */
  can_manage: boolean;
}

export interface SuggestionCounts {
  open: number;
  closed: number;
  total: number;
}

export interface SuggestionList {
  items: Suggestion[];
  counts: SuggestionCounts;
}
