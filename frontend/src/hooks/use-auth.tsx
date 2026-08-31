/**
 * Session state for the whole SPA.
 *
 * The browser holds no token: the backend sets HttpOnly cookies and this
 * context simply tracks who the server says we are. Every guard here is a
 * usability aid — the backend independently authorises every request.
 */
import { useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { ApiError, setSessionExpiredHandler } from "@/services/api";
import { authApi } from "@/services/endpoints";
import type { UserProfile } from "@/types";

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  mustChangePassword: boolean;
  login: (employeeId: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setUser: (user: UserProfile) => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = React.useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const queryClient = useQueryClient();

  const clearSession = React.useCallback(() => {
    setUserState(null);
    queryClient.clear();
  }, [queryClient]);

  // Restore the session on a hard reload: the cookies may still be valid.
  React.useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then((profile) => {
        if (!cancelled) setUserState(profile);
      })
      .catch(() => {
        if (!cancelled) setUserState(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The API client calls this when a silent refresh fails.
  React.useEffect(() => {
    setSessionExpiredHandler(() => {
      setUserState((current) => {
        if (current) toast.error("Your session has expired. Please sign in again.");
        return null;
      });
      queryClient.clear();
    });
  }, [queryClient]);

  const login = React.useCallback(
    async (employeeId: string, password: string) => {
      const response = await authApi.login(employeeId, password);
      setUserState(response.user);
      queryClient.clear();
      return response.user;
    },
    [queryClient],
  );

  const logout = React.useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // A failed logout must still clear local state.
      if (!(error instanceof ApiError)) throw error;
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const refreshUser = React.useCallback(async () => {
    try {
      setUserState(await authApi.me());
    } catch {
      clearSession();
    }
  }, [clearSession]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      isAdmin: user?.is_admin ?? false,
      mustChangePassword: user?.must_change_password ?? false,
      login,
      logout,
      refreshUser,
      setUser: setUserState,
    }),
    [user, isLoading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside an AuthProvider");
  return context;
}
