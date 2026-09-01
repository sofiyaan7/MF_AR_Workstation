/**
 * The per-project suggestion log.
 *
 * Any employee who can see the project can raise a suggestion here and read
 * every suggestion on it — open and closed alike. The log is shared on
 * purpose, so people can see what has already been asked for before asking
 * again. Closing and reopening is limited to the author and to admins; the
 * backend enforces that and `can_manage` mirrors the decision per row.
 */
import { CheckCircle2, CircleDot, MessageSquarePlus, RotateCcw } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateSuggestion, useSetSuggestionStatus, useSuggestions,
} from "@/hooks/use-suggestions";
import { formatRelative } from "@/lib/format";
import type { Suggestion, SuggestionStatus } from "@/types";

const TITLE_MIN = 4;
const TITLE_MAX = 200;

type Filter = "ALL" | SuggestionStatus;

function StatusBadge({ status }: { status: SuggestionStatus }) {
  return status === "OPEN" ? (
    <Badge variant="outline" className="gap-1 text-2xs">
      <CircleDot className="size-3" />
      Open
    </Badge>
  ) : (
    <Badge variant="muted" className="gap-1 text-2xs">
      <CheckCircle2 className="size-3" />
      Closed
    </Badge>
  );
}

function SuggestionRow({
  suggestion,
  onToggle,
  busy,
}: {
  suggestion: Suggestion;
  onToggle: (suggestion: Suggestion) => void;
  busy: boolean;
}) {
  const isOpen = suggestion.status === "OPEN";
  return (
    <li className="border-b border-border py-3 last:border-b-0 last:pb-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={suggestion.status} />
            <span className="text-sm font-medium text-foreground">{suggestion.title}</span>
          </div>
          {suggestion.body && (
            <p className="whitespace-pre-wrap text-xs text-muted-foreground">{suggestion.body}</p>
          )}
          <p className="text-2xs text-muted-foreground">
            {/* The author is null once their account is deleted; the log survives it. */}
            {suggestion.user?.full_name ?? "A former colleague"}
            {" · "}
            {formatRelative(suggestion.created_at)}
            {!isOpen && suggestion.closed_at && (
              <>
                {" · closed by "}
                {suggestion.closed_by?.full_name ?? "a former colleague"}
                {" "}
                {formatRelative(suggestion.closed_at)}
              </>
            )}
          </p>
        </div>
        {suggestion.can_manage && (
          <Button
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={() => onToggle(suggestion)}
            className="shrink-0 gap-1.5 text-xs"
          >
            {isOpen ? <CheckCircle2 className="size-3.5" /> : <RotateCcw className="size-3.5" />}
            {isOpen ? "Close" : "Reopen"}
          </Button>
        )}
      </div>
    </li>
  );
}

export function SuggestionBox({ projectId }: { projectId: number }) {
  const [filter, setFilter] = React.useState<Filter>("ALL");
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");

  const query = useSuggestions(projectId, filter === "ALL" ? undefined : filter);
  const create = useCreateSuggestion(projectId);
  const setStatus = useSetSuggestionStatus(projectId);

  const trimmed = title.trim();
  const canSubmit = trimmed.length >= TITLE_MIN && !create.isPending;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    try {
      await create.mutateAsync({ title: trimmed, body: body.trim() || null });
      setTitle("");
      setBody("");
    } catch {
      // The hook surfaces the failure as a toast; keep the draft so the text
      // the user typed is not thrown away.
    }
  };

  const counts = query.data?.counts;

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-sm">Suggestions</CardTitle>
        <p className="text-xs text-muted-foreground">
          Propose a change to this project. Everyone who can see the project can read the log.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={submit} className="space-y-2">
          <div className="space-y-1.5">
            <Label htmlFor="suggestion-title" className="text-xs">
              What should change?
            </Label>
            <Input
              id="suggestion-title"
              value={title}
              maxLength={TITLE_MAX}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Add a CSV export to the holdings table"
            />
          </div>
          <Textarea
            aria-label="More detail (optional)"
            value={body}
            rows={2}
            maxLength={5000}
            onChange={(event) => setBody(event.target.value)}
            placeholder="More detail (optional)"
            className="text-xs"
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-2xs text-muted-foreground">
              {trimmed.length > 0 && trimmed.length < TITLE_MIN
                ? `At least ${TITLE_MIN} characters.`
                : ""}
            </span>
            <Button type="submit" size="sm" disabled={!canSubmit} className="gap-1.5">
              <MessageSquarePlus className="size-3.5" />
              {create.isPending ? "Posting…" : "Post suggestion"}
            </Button>
          </div>
        </form>

        <Tabs value={filter} onValueChange={(value) => setFilter(value as Filter)}>
          <TabsList className="h-8">
            <TabsTrigger value="ALL" className="text-xs">
              All{counts ? ` (${counts.total})` : ""}
            </TabsTrigger>
            <TabsTrigger value="OPEN" className="text-xs">
              Open{counts ? ` (${counts.open})` : ""}
            </TabsTrigger>
            <TabsTrigger value="CLOSED" className="text-xs">
              Closed{counts ? ` (${counts.closed})` : ""}
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {query.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data && query.data.items.length > 0 ? (
          <ul className="-my-1">
            {query.data.items.map((suggestion) => (
              <SuggestionRow
                key={suggestion.id}
                suggestion={suggestion}
                busy={setStatus.isPending}
                onToggle={(item) =>
                  setStatus.mutate({
                    id: item.id,
                    status: item.status === "OPEN" ? "CLOSED" : "OPEN",
                  })
                }
              />
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={MessageSquarePlus}
            title={filter === "ALL" ? "No suggestions yet" : `Nothing ${filter.toLowerCase()}`}
            description={
              filter === "ALL"
                ? "Be the first to propose a change to this project."
                : "Try another tab."
            }
            className="py-8"
          />
        )}
      </CardContent>
    </Card>
  );
}
