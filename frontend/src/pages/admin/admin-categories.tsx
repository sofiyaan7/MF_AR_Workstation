import { FolderTree, MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import * as React from "react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/ui/page-header";
import { ICON_NAMES, ProjectIcon } from "@/components/ui/project-icon";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/ui/states";
import { useAdminCategories, useCategoryMutations } from "@/hooks/use-admin";
import { formatNumber } from "@/lib/format";
import type { CategoryDetail } from "@/types";

function CategoryDialog({
  open, onOpenChange, category,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  category: CategoryDetail | null;
}) {
  const isEdit = Boolean(category);
  const { create, update } = useCategoryMutations();

  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [icon, setIcon] = React.useState("Boxes");
  const [sortOrder, setSortOrder] = React.useState(0);

  React.useEffect(() => {
    if (open) {
      setName(category?.name ?? "");
      setDescription(category?.description ?? "");
      setIcon(category?.icon ?? "Boxes");
      setSortOrder(category?.sort_order ?? 0);
    }
  }, [open, category]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (name.trim().length < 2) return;
    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      icon,
      sort_order: sortOrder,
    };
    try {
      if (isEdit && category) await update.mutateAsync({ id: category.id, payload });
      else await create.mutateAsync(payload);
      onOpenChange(false);
    } catch {
      // Error already surfaced by the mutation hook.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Edit ${category?.name}` : "New category"}</DialogTitle>
          <DialogDescription>
            Categories group projects on the dashboard and drive the quick filters.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="category-name" required>
              Name
            </Label>
            <Input
              id="category-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Index Research"
              minLength={2}
              maxLength={80}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="category-description">Description</Label>
            <Input
              id="category-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Index reviews, rebalances and constituent research"
              maxLength={255}
            />
          </div>
          <div className="space-y-2">
            <Label>Icon</Label>
            <div className="flex flex-wrap gap-1.5">
              {ICON_NAMES.map((choice) => (
                <button
                  key={choice}
                  type="button"
                  onClick={() => setIcon(choice)}
                  aria-label={choice}
                  aria-pressed={icon === choice}
                  className={`rounded-lg border p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                    icon === choice ? "border-primary bg-primary/5" : "border-transparent hover:border-border"
                  }`}
                >
                  <ProjectIcon icon={choice} seed={choice} size="sm" />
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="category-sort">Sort order</Label>
            <Input
              id="category-sort"
              type="number"
              value={sortOrder}
              onChange={(event) => setSortOrder(Number(event.target.value) || 0)}
              className="w-28"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {isEdit ? "Save changes" : "Create category"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function AdminCategoriesPage() {
  const { data, isLoading, error, refetch } = useAdminCategories();
  const { remove } = useCategoryMutations();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<CategoryDetail | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<CategoryDetail | null>(null);

  return (
    <div>
      <PageHeader
        title="Categories"
        description="Group projects so employees can find them quickly."
        breadcrumbs={[{ label: "Home", to: "/" }, { label: "Admin" }, { label: "Categories" }]}
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus />
            New category
          </Button>
        }
      />

      {isLoading && <TableSkeleton rows={6} columns={4} />}
      {error && <ErrorState error={error} onRetry={() => refetch()} />}

      {!isLoading && !error && (data?.length ?? 0) === 0 && (
        <EmptyState
          icon={FolderTree}
          title="No categories yet"
          description="Create categories such as Research, Analytics or Automation to organise the catalogue."
          action={
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
            >
              <Plus />
              New category
            </Button>
          }
        />
      )}

      {!isLoading && !error && data && data.length > 0 && (
        <div className="surface overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Projects</TableHead>
                <TableHead className="text-right">Order</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((category) => (
                <TableRow key={category.id}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <ProjectIcon
                        icon={category.icon}
                        colour={category.colour}
                        seed={category.slug}
                        size="sm"
                      />
                      <div>
                        <p className="text-sm font-medium text-foreground">{category.name}</p>
                        <p className="font-mono text-2xs text-muted-foreground">{category.slug}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-sm text-sm text-muted-foreground">
                    <span className="line-clamp-1">{category.description || "—"}</span>
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {formatNumber(category.project_count)}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                    {category.sort_order}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${category.name}`}>
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() => {
                            setEditing(category);
                            setDialogOpen(true);
                          }}
                        >
                          <Pencil />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem destructive onSelect={() => setDeleteTarget(category)}>
                          <Trash2 />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CategoryDialog open={dialogOpen} onOpenChange={setDialogOpen} category={editing} />

      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{deleteTarget?.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget && deleteTarget.project_count > 0
                ? `${deleteTarget.project_count} project(s) still use this category. Move them elsewhere first — the portal will refuse the deletion otherwise.`
                : "This category will be removed from the filter list."}
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
              Delete category
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
