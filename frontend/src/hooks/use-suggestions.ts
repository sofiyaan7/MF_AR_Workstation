/** React Query hooks for a project's suggestion log. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api";
import { suggestionsApi } from "@/services/endpoints";
import type { SuggestionStatus } from "@/types";

export const suggestionKeys = {
  all: ["suggestions"] as const,
  list: (projectId: number, status?: SuggestionStatus) =>
    ["suggestions", projectId, status ?? "ALL"] as const,
};

export function useSuggestions(projectId: number, status?: SuggestionStatus) {
  return useQuery({
    queryKey: suggestionKeys.list(projectId, status),
    queryFn: () => suggestionsApi.list(projectId, status),
  });
}

function useInvalidate(projectId: number) {
  const queryClient = useQueryClient();
  // Every filtered view shares the same counts, so refresh them all rather
  // than just the tab the user happens to be on.
  return () =>
    queryClient.invalidateQueries({ queryKey: ["suggestions", projectId] });
}

export function useCreateSuggestion(projectId: number) {
  const invalidate = useInvalidate(projectId);
  return useMutation({
    mutationFn: (payload: { title: string; body?: string | null }) =>
      suggestionsApi.create(projectId, payload),
    onSuccess: () => {
      toast.success("Suggestion posted.");
      invalidate();
    },
    onError: (error: unknown) => {
      toast.error(
        error instanceof ApiError ? error.message : "Could not post that suggestion.",
      );
    },
  });
}

export function useSetSuggestionStatus(projectId: number) {
  const invalidate = useInvalidate(projectId);
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: SuggestionStatus }) =>
      suggestionsApi.setStatus(projectId, id, status),
    onSuccess: (suggestion) => {
      toast.success(suggestion.status === "CLOSED" ? "Suggestion closed." : "Suggestion reopened.");
      invalidate();
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : "Could not update that suggestion.");
    },
  });
}
