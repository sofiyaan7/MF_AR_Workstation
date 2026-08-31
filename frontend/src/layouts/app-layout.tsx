import * as React from "react";
import { Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

/** The signed-in shell: fixed sidebar, sticky topbar, scrolling content. */
export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const location = useLocation();

  // Close the mobile drawer whenever the route changes.
  React.useEffect(() => setSidebarOpen(false), [location.pathname]);

  return (
    <div className="flex h-full bg-background">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <Topbar onOpenSidebar={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto w-full max-w-[1600px] p-4 sm:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
