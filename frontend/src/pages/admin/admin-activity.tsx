import {
  Activity, CheckCircle2, Download, FilterX, LogIn, Search, ShieldAlert, Users, XCircle,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/ui/stat-card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, StatsSkeleton, TableSkeleton } from "@/components/ui/states";
import { useDebounce } from "@/hooks/use-debounce";
import { useAdminActivity, useAnalyticsOverview, useEventTypes } from "@/hooks/use-admin";
import { formatDateTime, humaniseEvent } from "@/lib/format";
import { downloadBlob } from "@/lib/utils";
import { adminActivityApi, type ActivityQuery } from "@/services/endpoints";

const ALL = "__all__";
const PAGE_SIZE = 50;

export function AdminActivityPage() {
  const [search, setSearch] = React.useState("");
  const [employeeId, setEmployeeId] = React.useState("");
  const [eventType, setEventType] = React.useState(ALL);
  const [outcome, setOutcome] = React.useState(ALL);
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(0);
  const [exporting, setExporting] = React.useState(false);

  const debouncedSearch = useDebounce(search, 250);
  const debouncedEmployeeId = useDebounce(employeeId, 250);

  const { data: overview, isLoading: overviewLoading } = useAnalyticsOverview();
  const { data: eventTypes } = useEventTypes();

  const filters: ActivityQuery = React.useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      employee_id: debouncedEmployeeId.trim() || undefined,
      event_type: eventType !== ALL ? [eventType] : undefined,
      success: outcome === ALL ? undefined : outcome === "success",
      // A bare date means "the whole of that day" to the person filtering.
      date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
    }),
    [debouncedSearch, debouncedEmployeeId, eventType, outcome, dateFrom, dateTo],
  );

  React.useEffect(() => setPage(0), [filters]);

  const { data, isLoading, error, refetch, isFetching } = useAdminActivity({
    ...filters,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const hasFilters =
    Boolean(debouncedSearch || debouncedEmployeeId || dateFrom || dateTo) ||
    eventType !== ALL ||
    outcome !== ALL;

  const clearFilters = () => {
    setSearch("");
    setEmployeeId("");
    setEventType(ALL);
    setOutcome(ALL);
    setDateFrom("");
    setDateTo("");
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await adminActivityApi.exportCsv(filters);
      const stamp = new Date().toISOString().slice(0, 10);
      downloadBlob(blob, `mf-ar-workstation-activity-${stamp}.csv`);
      toast.success("Activity exported", {
        description: hasFilters ? "The export matches your current filters." : undefined,
      });
    } catch {
      toast.error("Could not export the activity log.");
    } finally {
      setExporting(false);
    }
  };

  const total = data?.total ?? 0;
  const hasMore = (page + 1) * PAGE_SIZE < total;

  return (
    <div>
      <PageHeader
        title="Activity Logs"
        description="Every action taken in the portal, across all employees."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }, { label: "Activity Logs" }]}
        actions={
          <Button variant="outline" onClick={handleExport} loading={exporting}>
            {!exporting && <Download />}
            Export CSV
          </Button>
        }
      />

      {overviewLoading ? (
        <StatsSkeleton count={4} />
      ) : (
        overview && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Activities today" value={overview.activities_today} icon={Activity} />
            <StatCard label="Logins today" value={overview.logins_today} icon={LogIn} tone="success" />
            <StatCard
              label="Unique users today"
              value={overview.unique_active_users_today}
              icon={Users}
            />
            <StatCard
              label="Failed logins today"
              value={overview.failed_logins_today}
              icon={ShieldAlert}
              tone={overview.failed_logins_today > 0 ? "destructive" : "default"}
              hint={overview.locked_accounts > 0 ? `${overview.locked_accounts} account(s) locked` : undefined}
            />
          </div>
        )
      )}

      <div className="surface mb-4 space-y-3 p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-1.5">
            <Label htmlFor="activity-search" className="text-xs text-muted-foreground">
              Search
            </Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="activity-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Description, name or project"
                className="pl-9"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="activity-employee" className="text-xs text-muted-foreground">
              Employee ID
            </Label>
            <Input
              id="activity-employee"
              value={employeeId}
              onChange={(event) => setEmployeeId(event.target.value)}
              placeholder="ARWL12345"
              className="font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Event type</Label>
            <Select value={eventType} onValueChange={setEventType}>
              <SelectTrigger aria-label="Filter by event type">
                <SelectValue placeholder="All events" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All events</SelectItem>
                {(eventTypes ?? []).map((type) => (
                  <SelectItem key={type} value={type}>
                    {humaniseEvent(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Outcome</Label>
            <Select value={outcome} onValueChange={setOutcome}>
              <SelectTrigger aria-label="Filter by outcome">
                <SelectValue placeholder="Any outcome" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Any outcome</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failure">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="activity-from" className="text-xs text-muted-foreground">
              From
            </Label>
            <Input
              id="activity-from"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="activity-to" className="text-xs text-muted-foreground">
              To
            </Label>
            <Input
              id="activity-to"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </div>
          <div className="flex items-end xl:col-span-2">
            <Button variant="ghost" onClick={clearFilters} disabled={!hasFilters}>
              <FilterX />
              Clear filters
            </Button>
            <span className="ml-auto self-center text-xs text-muted-foreground">
              {isLoading ? "Loading…" : `${total.toLocaleString()} matching events`}
            </span>
          </div>
        </div>
      </div>

      {isLoading && <TableSkeleton rows={10} columns={6} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && data && data.items.length === 0 && (
        <EmptyState
          icon={Activity}
          title={hasFilters ? "No events match these filters" : "No activity recorded yet"}
          description={
            hasFilters
              ? "Try widening the date range or clearing a filter."
              : "Sign-ins and project launches will appear here as your team uses the portal."
          }
          action={
            hasFilters ? (
              <Button variant="outline" onClick={clearFilters}>
                <FilterX />
                Clear filters
              </Button>
            ) : undefined
          }
        />
      )}

      {!isLoading && !error && data && data.items.length > 0 && (
        <>
          <div className={`surface overflow-hidden ${isFetching ? "opacity-70" : ""}`}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Employee</TableHead>
                  <TableHead>Activity</TableHead>
                  <TableHead>Project</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Browser</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="whitespace-nowrap text-xs tabular-nums text-muted-foreground">
                      {formatDateTime(entry.timestamp)}
                    </TableCell>
                    <TableCell>
                      {entry.employee_id ? (
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {entry.user_name ?? "—"}
                          </p>
                          <p className="font-mono text-2xs text-muted-foreground">
                            {entry.employee_id}
                          </p>
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">Unknown</span>
                      )}
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <Badge variant="outline" className="mb-0.5 text-2xs">
                        {entry.event_type}
                      </Badge>
                      <p className="line-clamp-1 text-xs text-muted-foreground">
                        {entry.description}
                      </p>
                    </TableCell>
                    <TableCell className="max-w-[12rem] text-sm text-muted-foreground">
                      <span className="line-clamp-1">{entry.project_name ?? "—"}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {entry.ip_address ?? "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {entry.browser ?? "—"}
                    </TableCell>
                    <TableCell>
                      {entry.success ? (
                        <span className="flex items-center gap-1 text-xs text-success">
                          <CheckCircle2 className="size-3.5" />
                          Success
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-destructive">
                          <XCircle className="size-3.5" />
                          Failed
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0 || isFetching}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              Previous
            </Button>
            <span className="text-xs text-muted-foreground">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of{" "}
              {total.toLocaleString()}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore || isFetching}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
