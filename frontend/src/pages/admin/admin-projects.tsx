import {
  BarChart3, Copy, ExternalLink, Github, MoreHorizontal, Pencil, Plus, RotateCcw, Search,
  Trash2,
} from "lucide-react";
import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ProjectFormDialog } from "@/components/admin/project-form";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { ProjectIcon } from "@/components/ui/project-icon";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { ProjectStatusBadge, VisibilityBadge } from "@/components/ui/status-badge";
import { useDebounce } from "@/hooks/use-debounce";
import { useAdminProjects, useProjectMutations } from "@/hooks/use-admin";
import { useCategories } from "@/hooks/use-projects";
import { adminProjectsApi } from "@/services/endpoints";
import { formatNumber, formatRelative } from "@/lib/format";
import type { ProjectAdminDetail, ProjectAdminRow } from "@/types";

const ALL = "__all__";

export function AdminProjectsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [search, setSearch] = React.useState("");
  const [categoryId, setCategoryId] = React.useState(ALL);
  const [status, setStatus] = React.useState(ALL);
  const [includeDeleted, setIncludeDeleted] = React.useState(false);

  const [formOpen, setFormOpen] = React.useState(searchParams.get("new") === "1");
  const [editing, setEditing] = React.useState<ProjectAdminDetail | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<ProjectAdminRow | null>(null);

  const debouncedSearch = useDebounce(search, 250);
  const { data: categories } = useCategories();
  const { remove, duplicate, restore } = useProjectMutations();

  const query = React.useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      category_id: categoryId !== ALL ? Number(categoryId) : undefined,
      status: status !== ALL ? status : undefined,
      include_deleted: includeDeleted,
      limit: 200,
      sort: "updated",
    }),
    [debouncedSearch, categoryId, status, includeDeleted],
  );

  const { data, isLoading, error, refetch } = useAdminProjects(query);

  // Support /admin/projects?new=1 as a deep link from the dashboard.
  React.useEffect(() => {
    if (searchParams.get("new") === "1") {
      setEditing(null);
      setFormOpen(true);
      searchParams.delete("new");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = async (row: ProjectAdminRow) => {
    // Fetch the full record so permission lists are populated in the form.
    const detail = await adminProjectsApi.get(row.id);
    setEditing(detail);
    setFormOpen(true);
  };

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Add, edit and retire the projects shown across the portal."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }, { label: "Projects" }]}
        actions={
          <Button onClick={openCreate}>
            <Plus />
            Add project
          </Button>
        }
      />

      <div className="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search projects…"
            aria-label="Search projects"
            className="pl-9"
          />
        </div>
        <Select value={categoryId} onValueChange={setCategoryId}>
          <SelectTrigger className="lg:w-48" aria-label="Filter by category">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All categories</SelectItem>
            {(categories ?? []).map((category) => (
              <SelectItem key={category.id} value={String(category.id)}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="lg:w-44" aria-label="Filter by status">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            <SelectItem value="ACTIVE">Active</SelectItem>
            <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
            <SelectItem value="DEPRECATED">Deprecated</SelectItem>
            <SelectItem value="COMING_SOON">Coming soon</SelectItem>
          </SelectContent>
        </Select>
        <label className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
          <Switch checked={includeDeleted} onCheckedChange={setIncludeDeleted} />
          Show deleted
        </label>
      </div>

      {isLoading && <TableSkeleton rows={8} columns={7} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && data && data.items.length === 0 && (
        <EmptyState
          title={search ? "No projects match your search" : "No projects yet"}
          description={
            search
              ? "Try a different term or clear the filters."
              : "Add your first project — it appears on every employee dashboard immediately."
          }
          action={
            !search ? (
              <Button onClick={openCreate}>
                <Plus />
                Add project
              </Button>
            ) : undefined
          }
        />
      )}

      {!isLoading && !error && data && data.items.length > 0 && (
        <div className="surface overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Visibility</TableHead>
                <TableHead className="text-right">Opens</TableHead>
                <TableHead>Last opened</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((project) => (
                <TableRow key={project.id} className={project.is_deleted ? "opacity-55" : undefined}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <ProjectIcon
                        icon={project.icon}
                        colour={project.colour}
                        seed={project.slug}
                        size="sm"
                      />
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => navigate(`/admin/projects/${project.id}`)}
                            className="truncate rounded text-sm font-medium text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {project.name}
                          </button>
                          {project.is_featured && (
                            <Badge variant="default" className="text-2xs">
                              Featured
                            </Badge>
                          )}
                          {project.is_deleted && (
                            <Badge variant="destructive" className="text-2xs">
                              Deleted
                            </Badge>
                          )}
                          {!project.is_active && !project.is_deleted && (
                            <Badge variant="muted" className="text-2xs">
                              Disabled
                            </Badge>
                          )}
                          {project.repository_url && (
                            <a
                              href={project.repository_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(event) => event.stopPropagation()}
                              title={project.repository_url}
                              aria-label={`Open the ${project.name} repository`}
                              className="shrink-0 rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <Github className="size-3.5" />
                            </a>
                          )}
                        </div>
                        <a
                          href={project.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 truncate font-mono text-2xs text-muted-foreground transition-colors hover:text-foreground"
                        >
                          <ExternalLink className="size-2.5 shrink-0" />
                          <span className="truncate">{project.url}</span>
                        </a>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {project.category?.name ?? "—"}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {project.owner_name ?? "—"}
                  </TableCell>
                  <TableCell>
                    <ProjectStatusBadge status={project.status} />
                  </TableCell>
                  <TableCell>
                    <VisibilityBadge visibility={project.visibility} />
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {formatNumber(project.total_opens)}
                    <span className="ml-1 text-2xs text-muted-foreground">
                      / {formatNumber(project.unique_users)} users
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                    {project.last_opened_at ? formatRelative(project.last_opened_at) : "Never"}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${project.name}`}>
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => void openEdit(project)}>
                          <Pencil />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => navigate(`/admin/projects/${project.id}`)}>
                          <BarChart3 />
                          View analytics
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => duplicate.mutate(project.id)}>
                          <Copy />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {project.is_deleted ? (
                          <DropdownMenuItem onSelect={() => restore.mutate(project.id)}>
                            <RotateCcw />
                            Restore
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem destructive onSelect={() => setDeleteTarget(project)}>
                            <Trash2 />
                            Delete
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ProjectFormDialog open={formOpen} onOpenChange={setFormOpen} project={editing} />

      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{deleteTarget?.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              The project disappears from every employee dashboard straight away. This is a
              soft delete: the usage history stays in the activity log, and you can restore
              the project later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              destructive
              onClick={() => {
                if (deleteTarget) remove.mutate(deleteTarget.id);
                setDeleteTarget(null);
              }}
            >
              Delete project
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
