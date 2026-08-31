import { Loader2, Search, X } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { ProjectIcon } from "@/components/ui/project-icon";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/use-debounce";
import { useProjectList } from "@/hooks/use-projects";
import { cn } from "@/lib/utils";

/** Type-ahead across every project the signed-in employee is allowed to see. */
export function GlobalSearch() {
  const [term, setTerm] = React.useState("");
  const [open, setOpen] = React.useState(false);
  const [highlighted, setHighlighted] = React.useState(0);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const debounced = useDebounce(term, 200);
  const enabled = debounced.trim().length >= 2;
  const { data, isFetching } = useProjectList(
    enabled ? { search: debounced.trim(), limit: 8 } : { limit: 0 },
  );
  const results = enabled ? (data?.items ?? []) : [];

  React.useEffect(() => setHighlighted(0), [debounced]);

  React.useEffect(() => {
    const onClickAway = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickAway);
    return () => document.removeEventListener("mousedown", onClickAway);
  }, []);

  // "/" focuses search from anywhere, the way a keyboard-first tool should.
  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (event.key === "/" && !typing) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const go = (id: number) => {
    setOpen(false);
    setTerm("");
    navigate(`/projects/${id}`);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!results.length) {
      if (event.key === "Enter" && term.trim()) {
        setOpen(false);
        navigate(`/projects?search=${encodeURIComponent(term.trim())}`);
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((index) => (index - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(results[highlighted].id);
    }
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={inputRef}
        value={term}
        onChange={(event) => {
          setTerm(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search projects…"
        aria-label="Search projects"
        className="h-9 pl-9 pr-16"
      />
      <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
        {isFetching && enabled && <Loader2 className="size-3.5 animate-spin text-muted-foreground" />}
        {term ? (
          <button
            type="button"
            onClick={() => {
              setTerm("");
              inputRef.current?.focus();
            }}
            className="rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="size-3.5" />
          </button>
        ) : (
          <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 text-2xs font-medium text-muted-foreground sm:block">
            /
          </kbd>
        )}
      </div>

      {open && enabled && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-md border border-border bg-popover shadow-popover">
          {results.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              {isFetching ? "Searching…" : `No projects match “${debounced.trim()}”`}
            </p>
          ) : (
            <ul className="max-h-80 overflow-y-auto py-1 scrollbar-thin">
              {results.map((project, index) => (
                <li key={project.id}>
                  <button
                    type="button"
                    onMouseEnter={() => setHighlighted(index)}
                    onClick={() => go(project.id)}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2 text-left transition-colors",
                      index === highlighted ? "bg-accent" : "hover:bg-accent/60",
                    )}
                  >
                    <ProjectIcon icon={project.icon} colour={project.colour} seed={project.slug} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-foreground">{project.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {project.category?.name ?? "Uncategorised"}
                        {project.owner_name ? ` · ${project.owner_name}` : ""}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
