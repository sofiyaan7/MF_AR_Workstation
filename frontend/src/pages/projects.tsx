import { FilterX, LayoutGrid, Search, SlidersHorizontal } from "lucide-react";
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { ProjectGrid } from "@/components/projects/project-grid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useDebounce } from "@/hooks/use-debounce";
import {
  useCategories, useProjectList, useProjectOwners, useProjectTags,
} from "@/hooks/use-projects";
import { cn } from "@/lib/utils";

const ALL = "__all__";

const SORT_OPTIONS = [
  { value: "featured", label: "Featured first" },
  { value: "name", label: "Name (A–Z)" },
  { value: "recent", label: "Recently added" },
  { value: "updated", label: "Recently updated" },
  { value: "most_used", label: "Most used" },
];

const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Active" },
  { value: "MAINTENANCE", label: "Maintenance" },
  { value: "DEPRECATED", label: "Deprecated" },
  { value: "COMING_SOON", label: "Coming soon" },
];

export function ProjectsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [search, setSearch] = React.useState(searchParams.get("search") ?? "");
  const [categoryId, setCategoryId] = React.useState(searchParams.get("category_id") ?? ALL);
  const [owner, setOwner] = React.useState(searchParams.get("owner") ?? ALL);
  const [status, setStatus] = React.useState(searchParams.get("status") ?? ALL);
  const [sort, setSort] = React.useState(searchParams.get("sort") ?? "featured");
  const [activeTags, setActiveTags] = React.useState<string[]>(searchParams.getAll("tag"));
  const [showFilters, setShowFilters] = React.useState(false);

  const debouncedSearch = useDebounce(search, 250);

  const { data: categories } = useCategories();
  const { data: tags } = useProjectTags();
  const { data: owners } = useProjectOwners();

  const query = React.useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      category_id: categoryId !== ALL ? Number(categoryId) : undefined,
      owner: owner !== ALL ? owner : undefined,
      status: status !== ALL ? status : undefined,
      tag: activeTags.length ? activeTags : undefined,
      sort,
      limit: 120,
    }),
    [debouncedSearch, categoryId, owner, status, activeTags, sort],
  );

  // Keep the URL shareable and reload-safe.
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedSearch.trim()) params.set("search", debouncedSearch.trim());
    if (categoryId !== ALL) params.set("category_id", categoryId);
    if (owner !== ALL) params.set("owner", owner);
    if (status !== ALL) params.set("status", status);
    if (sort !== "featured") params.set("sort", sort);
    activeTags.forEach((tag) => params.append("tag", tag));
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, categoryId, owner, status, sort, activeTags, setSearchParams]);

  const { data, isLoading, isFetching, error, refetch } = useProjectList(query);

  const filterCount =
    (categoryId !== ALL ? 1 : 0) +
    (owner !== ALL ? 1 : 0) +
    (status !== ALL ? 1 : 0) +
    activeTags.length;

  const clearFilters = () => {
    setSearch("");
    setCategoryId(ALL);
    setOwner(ALL);
    setStatus(ALL);
    setActiveTags([]);
    setSort("featured");
  };

  const toggleTag = (name: string) =>
    setActiveTags((current) =>
      current.includes(name) ? current.filter((tag) => tag !== name) : [...current, name],
    );

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Every tool and dashboard you have access to."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Projects" }]}
        actions={
          <span className="text-sm text-muted-foreground">
            {isLoading ? "Loading…" : `${data?.total ?? 0} project${data?.total === 1 ? "" : "s"}`}
          </span>
        }
      />

      {/* Category quick-filter row */}
      {categories && categories.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setCategoryId(ALL)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              categoryId === ALL
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            All
          </button>
          {categories.map((category) => (
            <button
              key={category.id}
              type="button"
              onClick={() => setCategoryId(String(category.id))}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                categoryId === String(category.id)
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              {category.name}
              <span className="ml-1.5 opacity-60">{category.project_count}</span>
            </button>
          ))}
        </div>
      )}

      {/* Search + sort */}
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, description, tag or owner…"
            aria-label="Search projects"
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showFilters || filterCount > 0 ? "secondary" : "outline"}
            size="default"
            onClick={() => setShowFilters((visible) => !visible)}
            aria-expanded={showFilters}
          >
            <SlidersHorizontal />
            Filters
            {filterCount > 0 && (
              <Badge variant="default" className="ml-0.5 px-1.5 py-0">
                {filterCount}
              </Badge>
            )}
          </Button>
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger className="w-[170px]" aria-label="Sort projects">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {showFilters && (
        <div className="surface mb-4 animate-fade-in space-y-4 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Owner</label>
              <Select value={owner} onValueChange={setOwner}>
                <SelectTrigger>
                  <SelectValue placeholder="Any owner" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Any owner</SelectItem>
                  {(owners ?? []).map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Status</label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Any status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>Any status</SelectItem>
                  {STATUS_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                variant="ghost"
                onClick={clearFilters}
                disabled={filterCount === 0 && !search}
                className="w-full"
              >
                <FilterX />
                Clear all
              </Button>
            </div>
          </div>

          {tags && tags.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">Tags</p>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => toggleTag(tag.name)}
                    className={cn(
                      "rounded-md border px-2 py-0.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      activeTags.includes(tag.name)
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
                    )}
                    aria-pressed={activeTags.includes(tag.name)}
                  >
                    {tag.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className={cn(isFetching && !isLoading && "opacity-60 transition-opacity")}>
        <ProjectGrid
          projects={data?.items}
          isLoading={isLoading}
          error={error}
          onRetry={() => refetch()}
          emptyTitle={
            search || filterCount > 0 ? "No projects match your filters" : "No projects available"
          }
          emptyDescription={
            search || filterCount > 0
              ? "Try a different search term, or clear the filters to see everything."
              : "Once an administrator grants you access to a project, it appears here."
          }
          emptyAction={
            search || filterCount > 0 ? (
              <Button variant="outline" onClick={clearFilters}>
                <LayoutGrid />
                Show all projects
              </Button>
            ) : undefined
          }
          skeletonCount={8}
        />
      </div>
    </div>
  );
}
