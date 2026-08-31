import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@radix-ui/react-tooltip";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { RequireAdmin, RequireAuth } from "@/components/layout/route-guards";
import { AppLayout } from "@/layouts/app-layout";
import { AuthProvider } from "@/hooks/use-auth";
import { ThemeProvider, useTheme } from "@/hooks/use-theme";
import { ApiError } from "@/services/api";

import { DashboardPage } from "@/pages/dashboard";
import { FavouritesPage } from "@/pages/favourites";
import { LoginPage } from "@/pages/login";
import { MyActivityPage } from "@/pages/my-activity";
import { NotFoundPage } from "@/pages/not-found";
import { ProfilePage } from "@/pages/profile";
import { ProjectDetailPage } from "@/pages/project-detail";
import { ProjectsPage } from "@/pages/projects";
import { RecentPage } from "@/pages/recent";
import { SecurityPage } from "@/pages/security";
import { AdminActivityPage } from "@/pages/admin/admin-activity";
import { AdminAnalyticsPage } from "@/pages/admin/admin-analytics";
import { AdminCategoriesPage } from "@/pages/admin/admin-categories";
import { AdminProjectDetailPage } from "@/pages/admin/admin-project-detail";
import { AdminProjectsPage } from "@/pages/admin/admin-projects";
import { AdminUsersPage } from "@/pages/admin/admin-users";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Never retry an auth or permission failure — it will not change.
        if (error instanceof ApiError && [401, 403, 404].includes(error.status)) return false;
        return failureCount < 2;
      },
    },
  },
});

function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      position="bottom-right"
      theme={resolvedTheme}
      richColors
      closeButton
      duration={4000}
      toastOptions={{ className: "font-sans" }}
    />
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <TooltipProvider delayDuration={300}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />

                <Route element={<RequireAuth />}>
                  <Route element={<AppLayout />}>
                    <Route index element={<DashboardPage />} />
                    <Route path="projects" element={<ProjectsPage />} />
                    <Route path="projects/:projectId" element={<ProjectDetailPage />} />
                    <Route path="favourites" element={<FavouritesPage />} />
                    <Route path="recent" element={<RecentPage />} />
                    <Route path="activity" element={<MyActivityPage />} />
                    <Route path="profile" element={<ProfilePage />} />
                    <Route path="security" element={<SecurityPage />} />

                    <Route path="admin" element={<RequireAdmin />}>
                      <Route index element={<Navigate to="/admin/analytics" replace />} />
                      <Route path="users" element={<AdminUsersPage />} />
                      <Route path="projects" element={<AdminProjectsPage />} />
                      <Route path="projects/:projectId" element={<AdminProjectDetailPage />} />
                      <Route path="categories" element={<AdminCategoriesPage />} />
                      <Route path="activity" element={<AdminActivityPage />} />
                      <Route path="analytics" element={<AdminAnalyticsPage />} />
                    </Route>

                    <Route path="*" element={<NotFoundPage />} />
                  </Route>
                </Route>
              </Routes>
              <ThemedToaster />
            </TooltipProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
