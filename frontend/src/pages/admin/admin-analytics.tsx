import {
  Activity, BarChart3, FolderKanban, LogIn, MousePointerClick, ShieldAlert, TrendingUp, Users,
} from "lucide-react";
import * as React from "react";

import { BarList, TrendChart, UsageBarChart } from "@/components/admin/charts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState, StatsSkeleton } from "@/components/ui/states";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalytics } from "@/hooks/use-admin";
import { formatNumber } from "@/lib/format";

const PERIODS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
];

export function AdminAnalyticsPage() {
  const [days, setDays] = React.useState("30");
  const { data, isLoading, error, refetch } = useAnalytics(Number(days));

  const overview = data?.overview;

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Portal adoption and project usage, computed live from the audit data."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }, { label: "Analytics" }]}
        actions={
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-40" aria-label="Reporting period">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PERIODS.map((period) => (
                <SelectItem key={period.value} value={period.value}>
                  {period.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {isLoading && (
        <div className="space-y-6">
          <StatsSkeleton count={4} />
          <StatsSkeleton count={4} />
          <Skeleton className="h-72" />
        </div>
      )}

      {!isLoading && !error && data && overview && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Total employees"
              value={overview.total_users}
              hint={`${formatNumber(overview.active_users)} active`}
              icon={Users}
            />
            <StatCard
              label="Total projects"
              value={overview.total_projects}
              hint={`${formatNumber(overview.active_projects)} live · ${formatNumber(overview.projects_added_this_month)} added this month`}
              icon={FolderKanban}
            />
            <StatCard
              label="Logins today"
              value={overview.logins_today}
              hint={`${formatNumber(overview.unique_active_users_today)} unique users active`}
              icon={LogIn}
              tone="success"
            />
            <StatCard
              label="Failed logins today"
              value={overview.failed_logins_today}
              hint={overview.locked_accounts > 0 ? `${overview.locked_accounts} locked account(s)` : "No locked accounts"}
              icon={ShieldAlert}
              tone={overview.failed_logins_today > 0 ? "destructive" : "default"}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Project opens today"
              value={overview.project_opens_today}
              icon={MousePointerClick}
            />
            <StatCard
              label="Total project opens"
              value={overview.total_project_opens}
              icon={TrendingUp}
            />
            <StatCard label="Activities today" value={overview.activities_today} icon={Activity} />
            <StatCard
              label="Most viewed project"
              value={overview.most_viewed_project?.name ?? "—"}
              hint={
                overview.most_viewed_project
                  ? `${formatNumber(overview.most_viewed_project.opens)} opens`
                  : "No opens recorded yet"
              }
              icon={BarChart3}
            />
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Portal engagement</CardTitle>
              <CardDescription>
                Daily activity over the {days === "7" ? "last week" : `last ${days} days`}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="dau">
                <TabsList>
                  <TabsTrigger value="dau">Daily active users</TabsTrigger>
                  <TabsTrigger value="logins">Logins</TabsTrigger>
                  <TabsTrigger value="opens">Project opens</TabsTrigger>
                </TabsList>
                <TabsContent value="dau">
                  <TrendChart data={data.daily_active_users} valueLabel="active users" colourIndex={0} />
                </TabsContent>
                <TabsContent value="logins">
                  <TrendChart data={data.daily_logins} valueLabel="logins" colourIndex={1} />
                </TabsContent>
                <TabsContent value="opens">
                  <TrendChart data={data.daily_project_opens} valueLabel="project opens" colourIndex={2} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Project usage</CardTitle>
                <CardDescription>Most-opened projects in this period.</CardDescription>
              </CardHeader>
              <CardContent>
                <UsageBarChart
                  data={data.project_usage.map((row) => ({
                    label: row.project_name,
                    value: row.opens,
                  }))}
                  valueLabel="opens"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Most active employees</CardTitle>
                <CardDescription>Ranked by project launches in this period.</CardDescription>
              </CardHeader>
              <CardContent>
                <BarList
                  items={data.top_users.map((user) => ({
                    label: user.full_name,
                    value: user.opens,
                    hint: `${user.employee_id}${user.department ? ` · ${user.department}` : ""}`,
                  }))}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Catalogue by category</CardTitle>
                <CardDescription>How the project catalogue is distributed.</CardDescription>
              </CardHeader>
              <CardContent>
                <BarList
                  items={data.category_breakdown.map((row) => ({
                    label: row.category,
                    value: row.projects,
                    hint: `${formatNumber(row.opens)} total opens`,
                  }))}
                  valueLabel="projects"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Sign-in trends</CardTitle>
                <CardDescription>Successful and failed attempts over time.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "Today", ok: data.login_trends.successful_today, bad: data.login_trends.failed_today },
                    { label: "7 days", ok: data.login_trends.successful_week, bad: data.login_trends.failed_week },
                    { label: "30 days", ok: data.login_trends.successful_month, bad: data.login_trends.failed_month },
                  ].map((period) => (
                    <div key={period.label} className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">{period.label}</p>
                      <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                        {formatNumber(period.ok)}
                      </p>
                      <p className="text-2xs text-muted-foreground">successful</p>
                      <p
                        className={`mt-2 text-sm font-medium tabular-nums ${
                          period.bad > 0 ? "text-destructive" : "text-muted-foreground"
                        }`}
                      >
                        {formatNumber(period.bad)}
                      </p>
                      <p className="text-2xs text-muted-foreground">failed</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
