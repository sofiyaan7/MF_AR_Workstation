import {
  Activity, CheckCircle2, FolderOpen, KeyRound, LogIn, LogOut, Star, UserCog, XCircle,
} from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useMyActivity } from "@/hooks/use-admin";
import { dayLabel, formatTime, humaniseEvent } from "@/lib/format";
import type { MyActivityEntry } from "@/types";

const EVENT_ICONS: Record<string, typeof Activity> = {
  LOGIN: LogIn,
  LOGOUT: LogOut,
  FAILED_LOGIN: XCircle,
  PASSWORD_CHANGED: KeyRound,
  PASSWORD_RESET: KeyRound,
  PROJECT_OPENED: FolderOpen,
  PROJECT_VIEWED: FolderOpen,
  PROJECT_FAVOURITED: Star,
  PROJECT_UNFAVOURITED: Star,
  PROFILE_UPDATED: UserCog,
};

const PAGE_SIZE = 50;

function groupByDay(entries: MyActivityEntry[]): [string, MyActivityEntry[]][] {
  const groups = new Map<string, MyActivityEntry[]>();
  for (const entry of entries) {
    const key = dayLabel(entry.timestamp);
    const bucket = groups.get(key);
    if (bucket) bucket.push(entry);
    else groups.set(key, [entry]);
  }
  return Array.from(groups.entries());
}

export function MyActivityPage() {
  const [page, setPage] = React.useState(0);
  const { data, isLoading, error, refetch, isFetching } = useMyActivity({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const grouped = React.useMemo(() => groupByDay(data?.items ?? []), [data?.items]);
  const total = data?.total ?? 0;
  const hasMore = (page + 1) * PAGE_SIZE < total;

  return (
    <div>
      <PageHeader
        title="My Activity"
        description="A record of your own actions in the portal. Only you and administrators can see this."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "My Activity" }]}
        actions={
          total > 0 ? (
            <span className="text-sm text-muted-foreground">{total} recorded events</span>
          ) : null
        }
      />

      {isLoading && <TableSkeleton rows={8} columns={3} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && grouped.length === 0 && (
        <EmptyState
          icon={Activity}
          title="No activity recorded yet"
          description="Signing in, opening projects and changing your settings will show up here."
        />
      )}

      {!isLoading && !error && grouped.length > 0 && (
        <div className="space-y-6">
          {grouped.map(([day, entries]) => (
            <section key={day}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {day}
              </h2>
              <ul className="surface divide-y divide-border">
                {entries.map((entry) => {
                  const Icon = EVENT_ICONS[entry.event_type] ?? Activity;
                  return (
                    <li key={entry.id} className="flex items-start gap-3 px-4 py-3">
                      <div
                        className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md ${
                          entry.success ? "bg-muted text-muted-foreground" : "bg-destructive/10 text-destructive"
                        }`}
                      >
                        <Icon className="size-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground">
                          {entry.description || humaniseEvent(entry.event_type)}
                        </p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                          <span className="tabular-nums">{formatTime(entry.timestamp)}</span>
                          {entry.project_name && <span>· {entry.project_name}</span>}
                          {entry.browser && <span>· {entry.browser}</span>}
                          {entry.ip_address && <span className="font-mono">· {entry.ip_address}</span>}
                        </p>
                      </div>
                      {entry.success ? (
                        <CheckCircle2 className="mt-1 size-4 shrink-0 text-success" aria-label="Success" />
                      ) : (
                        <Badge variant="destructive">Failed</Badge>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}

          {(page > 0 || hasMore) && (
            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0 || isFetching}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
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
          )}
        </div>
      )}
    </div>
  );
}
