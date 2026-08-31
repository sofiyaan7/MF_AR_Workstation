/** Per-employee audit view: their activity trail and their login attempts. */
import { CheckCircle2, XCircle } from "lucide-react";

import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState, TableSkeleton } from "@/components/ui/states";
import { useUserActivity, useUserLoginHistory } from "@/hooks/use-admin";
import { formatDateTime, humaniseEvent } from "@/lib/format";
import type { UserAdminView } from "@/types";

interface UserActivityDialogProps {
  target: { user: UserAdminView; tab: "activity" | "logins" } | null;
  onClose: () => void;
}

export function UserActivityDialog({ target, onClose }: UserActivityDialogProps) {
  const userId = target?.user.id ?? 0;
  const activity = useUserActivity(userId);
  const logins = useUserLoginHistory(userId);

  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="xl">
        <DialogHeader>
          <DialogTitle>{target?.user.full_name}</DialogTitle>
          <DialogDescription>
            <span className="font-mono">{target?.user.employee_id}</span>
            {target?.user.department ? ` · ${target.user.department}` : ""}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue={target?.tab ?? "activity"}>
          <TabsList>
            <TabsTrigger value="activity">Activity</TabsTrigger>
            <TabsTrigger value="logins">Login history</TabsTrigger>
          </TabsList>

          <TabsContent value="activity">
            {activity.isLoading ? (
              <TableSkeleton rows={6} columns={3} />
            ) : (activity.data?.items.length ?? 0) === 0 ? (
              <EmptyState title="No activity recorded" />
            ) : (
              <ul className="max-h-96 divide-y divide-border overflow-y-auto scrollbar-thin rounded-md border border-border">
                {activity.data?.items.map((entry) => (
                  <li key={entry.id} className="flex items-start gap-3 px-3 py-2.5">
                    {entry.success ? (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
                    ) : (
                      <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-foreground">
                        {entry.description || humaniseEvent(entry.event_type)}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatDateTime(entry.timestamp)}
                        {entry.ip_address && ` · ${entry.ip_address}`}
                        {entry.browser && ` · ${entry.browser}`}
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0 text-2xs">
                      {entry.event_type}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="logins">
            {logins.isLoading ? (
              <TableSkeleton rows={6} columns={3} />
            ) : (logins.data?.items.length ?? 0) === 0 ? (
              <EmptyState title="No sign-in attempts recorded" />
            ) : (
              <ul className="max-h-96 divide-y divide-border overflow-y-auto scrollbar-thin rounded-md border border-border">
                {logins.data?.items.map((attempt) => (
                  <li key={attempt.id} className="flex items-center gap-3 px-3 py-2.5">
                    {attempt.successful ? (
                      <CheckCircle2 className="size-4 shrink-0 text-success" />
                    ) : (
                      <XCircle className="size-4 shrink-0 text-destructive" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-foreground">
                        {attempt.successful ? "Successful sign-in" : "Failed sign-in"}
                        {attempt.failure_reason && (
                          <span className="text-muted-foreground"> · {attempt.failure_reason}</span>
                        )}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(attempt.attempted_at)}
                        {attempt.ip_address && ` · ${attempt.ip_address}`}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
