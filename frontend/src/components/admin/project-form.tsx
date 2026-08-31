/**
 * Create / edit a project.
 *
 * This form is the whole "add a project without changing code" workflow: an
 * admin fills it in, saves, and the card appears on the dashboard for everyone
 * the visibility rules allow.
 */
import { Plus, X } from "lucide-react";
import * as React from "react";

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ICON_NAMES, ProjectIcon } from "@/components/ui/project-icon";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useCategories } from "@/hooks/use-projects";
import { useProjectMutations } from "@/hooks/use-admin";
import { cn } from "@/lib/utils";
import type { ProjectDetail, ProjectFormValues, ProjectStatus, Visibility } from "@/types";

const NO_CATEGORY = "__none__";

const STATUS_CHOICES: { value: ProjectStatus; label: string; hint: string }[] = [
  { value: "ACTIVE", label: "Active", hint: "Live and available to open" },
  { value: "MAINTENANCE", label: "Maintenance", hint: "Available, but flagged as under work" },
  { value: "DEPRECATED", label: "Deprecated", hint: "Still listed, discouraged for new use" },
  { value: "COMING_SOON", label: "Coming soon", hint: "Visible but cannot be opened yet" },
];

const VISIBILITY_CHOICES: { value: Visibility; label: string; hint: string }[] = [
  { value: "ALL_EMPLOYEES", label: "All employees", hint: "Everyone with a portal account" },
  { value: "SPECIFIC_EMPLOYEES", label: "Specific employees", hint: "Only the Employee IDs you list" },
  { value: "ADMIN_ONLY", label: "Admins only", hint: "Hidden from standard employees" },
];

function emptyForm(): ProjectFormValues {
  return {
    name: "",
    url: "",
    description: "",
    short_description: "",
    documentation_url: "",
    category_id: null,
    tags: [],
    owner_name: "",
    icon: "LayoutDashboard",
    status: "ACTIVE",
    visibility: "ALL_EMPLOYEES",
    allowed_employee_ids: [],
    allowed_departments: [],
    is_featured: false,
    open_in_new_tab: true,
    sort_order: 0,
    is_active: true,
  };
}

function fromProject(project: ProjectDetail): ProjectFormValues {
  return {
    name: project.name,
    url: project.url,
    description: project.description ?? "",
    short_description: project.short_description ?? "",
    documentation_url: project.documentation_url ?? "",
    category_id: project.category?.id ?? null,
    tags: project.tags.map((tag) => tag.name),
    owner_name: project.owner_name ?? "",
    icon: project.icon,
    status: project.status,
    visibility: project.visibility,
    allowed_employee_ids: project.allowed_employee_ids,
    allowed_departments: project.allowed_departments,
    is_featured: project.is_featured,
    open_in_new_tab: project.open_in_new_tab,
    sort_order: project.sort_order,
    is_active: project.is_active,
  };
}

/** Comma / Enter separated chips, used for both tags and Employee IDs. */
function ChipInput({
  id, label, values, onChange, placeholder, hint, mono,
}: {
  id: string;
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder: string;
  hint?: string;
  mono?: boolean;
}) {
  const [draft, setDraft] = React.useState("");

  const commit = (raw: string) => {
    const parts = raw
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .filter((part) => !values.some((value) => value.toLowerCase() === part.toLowerCase()));
    if (parts.length) onChange([...values, ...parts]);
    setDraft("");
  };

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={draft}
        onChange={(event) => {
          const value = event.target.value;
          if (value.endsWith(",")) commit(value);
          else setDraft(value);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit(draft);
          } else if (event.key === "Backspace" && !draft && values.length) {
            onChange(values.slice(0, -1));
          }
        }}
        onBlur={() => draft.trim() && commit(draft)}
        placeholder={placeholder}
        className={cn(mono && "font-mono")}
      />
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {values.map((value) => (
            <Badge key={value} variant="secondary" className={cn("gap-1", mono && "font-mono")}>
              {value}
              <button
                type="button"
                onClick={() => onChange(values.filter((item) => item !== value))}
                className="rounded-sm transition-opacity hover:opacity-70"
                aria-label={`Remove ${value}`}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

interface ProjectFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project?: ProjectDetail | null;
}

export function ProjectFormDialog({ open, onOpenChange, project }: ProjectFormDialogProps) {
  const isEdit = Boolean(project);
  const { data: categories } = useCategories();
  const { create, update } = useProjectMutations();

  const [values, setValues] = React.useState<ProjectFormValues>(emptyForm);
  const [touched, setTouched] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setValues(project ? fromProject(project) : emptyForm());
      setTouched(false);
    }
  }, [open, project]);

  const set = <K extends keyof ProjectFormValues>(key: K, value: ProjectFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  const urlValid = /^https?:\/\/.+/i.test(values.url.trim());
  const nameValid = values.name.trim().length >= 2;
  const canSubmit = nameValid && urlValid && !create.isPending && !update.isPending;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (!canSubmit) return;

    const payload: ProjectFormValues = {
      ...values,
      name: values.name.trim(),
      url: values.url.trim(),
      owner_name: values.owner_name?.trim() || null,
      description: values.description?.trim() || null,
      short_description: values.short_description?.trim() || null,
      documentation_url: values.documentation_url?.trim() || null,
    };

    try {
      if (isEdit && project) await update.mutateAsync({ id: project.id, payload });
      else await create.mutateAsync(payload);
      onOpenChange(false);
    } catch {
      // The mutation hook has already surfaced a toast; keep the form open.
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="xl" className="max-h-[calc(100vh-2rem)]">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Edit ${project?.name}` : "Add project"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Changes apply immediately for everyone who can see this project."
              : "The project card appears on the dashboard as soon as you save — no code change needed."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* --- Basics ------------------------------------------------- */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="project-name" required>
                Project name
              </Label>
              <Input
                id="project-name"
                value={values.name}
                onChange={(event) => set("name", event.target.value)}
                placeholder="MSCI August Review"
                aria-invalid={touched && !nameValid}
                required
              />
              {touched && !nameValid && (
                <p className="text-xs text-destructive">Enter a name of at least 2 characters.</p>
              )}
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="project-url" required>
                Project URL
              </Label>
              <Input
                id="project-url"
                value={values.url}
                onChange={(event) => set("url", event.target.value)}
                placeholder="https://example.internal/msci-august"
                className="font-mono text-xs"
                aria-invalid={touched && !urlValid}
                required
              />
              <p className="text-xs text-muted-foreground">
                Any http(s) address — Streamlit, React, Voilà, an internal host, anything.
              </p>
              {touched && !urlValid && (
                <p className="text-xs text-destructive">
                  Enter a full URL starting with http:// or https://
                </p>
              )}
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="project-short">Short description</Label>
              <Input
                id="project-short"
                value={values.short_description ?? ""}
                onChange={(event) => set("short_description", event.target.value)}
                placeholder="Automated MSCI index review analysis and backtesting."
                maxLength={280}
              />
              <p className="text-xs text-muted-foreground">Shown on the project card.</p>
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="project-description">Full description</Label>
              <Textarea
                id="project-description"
                value={values.description ?? ""}
                onChange={(event) => set("description", event.target.value)}
                placeholder="What the project does, who it is for, and anything users should know."
                rows={3}
                maxLength={5000}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="project-category">Category</Label>
              <Select
                value={values.category_id ? String(values.category_id) : NO_CATEGORY}
                onValueChange={(value) =>
                  set("category_id", value === NO_CATEGORY ? null : Number(value))
                }
              >
                <SelectTrigger id="project-category">
                  <SelectValue placeholder="Choose a category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_CATEGORY}>Uncategorised</SelectItem>
                  {(categories ?? []).map((category) => (
                    <SelectItem key={category.id} value={String(category.id)}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="project-owner">Project owner</Label>
              <Input
                id="project-owner"
                value={values.owner_name ?? ""}
                onChange={(event) => set("owner_name", event.target.value)}
                placeholder="Sofiyaan Sameer"
              />
            </div>

            <div className="sm:col-span-2">
              <ChipInput
                id="project-tags"
                label="Tags"
                values={values.tags}
                onChange={(tags) => set("tags", tags)}
                placeholder="MSCI, Research, Backtesting — press Enter after each"
                hint="Tags feed the search and the tag filters."
              />
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="project-docs">Documentation URL</Label>
              <Input
                id="project-docs"
                value={values.documentation_url ?? ""}
                onChange={(event) => set("documentation_url", event.target.value)}
                placeholder="https://wiki.internal/msci-review (optional)"
                className="font-mono text-xs"
              />
            </div>
          </div>

          <Separator />

          {/* --- Icon --------------------------------------------------- */}
          <div className="space-y-2">
            <Label>Icon</Label>
            <div className="flex flex-wrap gap-1.5">
              {ICON_NAMES.map((icon) => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => set("icon", icon)}
                  aria-label={icon}
                  aria-pressed={values.icon === icon}
                  className={cn(
                    "rounded-lg border p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    values.icon === icon
                      ? "border-primary bg-primary/5"
                      : "border-transparent hover:border-border",
                  )}
                >
                  <ProjectIcon icon={icon} seed={values.name || icon} size="sm" />
                </button>
              ))}
            </div>
          </div>

          <Separator />

          {/* --- Status & visibility ------------------------------------ */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="project-status">Status</Label>
              <Select
                value={values.status}
                onValueChange={(value) => set("status", value as ProjectStatus)}
              >
                <SelectTrigger id="project-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_CHOICES.map((choice) => (
                    <SelectItem key={choice.value} value={choice.value}>
                      {choice.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {STATUS_CHOICES.find((choice) => choice.value === values.status)?.hint}
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="project-visibility">Visibility</Label>
              <Select
                value={values.visibility}
                onValueChange={(value) => set("visibility", value as Visibility)}
              >
                <SelectTrigger id="project-visibility">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VISIBILITY_CHOICES.map((choice) => (
                    <SelectItem key={choice.value} value={choice.value}>
                      {choice.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {VISIBILITY_CHOICES.find((choice) => choice.value === values.visibility)?.hint}
              </p>
            </div>

            {values.visibility === "SPECIFIC_EMPLOYEES" && (
              <div className="sm:col-span-2">
                <ChipInput
                  id="project-employees"
                  label="Permitted Employee IDs"
                  values={values.allowed_employee_ids}
                  onChange={(ids) => set("allowed_employee_ids", ids)}
                  placeholder="ARWL12345, ARWL12346 — press Enter after each"
                  hint="Only these employees will see the project. Unknown IDs are ignored."
                  mono
                />
              </div>
            )}

            {values.visibility === "ALL_EMPLOYEES" && (
              <div className="sm:col-span-2">
                <ChipInput
                  id="project-departments"
                  label="Restrict to departments (optional)"
                  values={values.allowed_departments}
                  onChange={(departments) => set("allowed_departments", departments)}
                  placeholder="Research, Portfolio — leave empty for everyone"
                  hint="Leave empty to show the project to every employee."
                />
              </div>
            )}
          </div>

          <Separator />

          {/* --- Options ------------------------------------------------ */}
          <div className="space-y-3">
            {[
              {
                key: "is_active" as const,
                label: "Enabled",
                hint: "Disabled projects are hidden from employees but keep their history.",
              },
              {
                key: "is_featured" as const,
                label: "Featured",
                hint: "Pins the project to the top of the dashboard.",
              },
              {
                key: "open_in_new_tab" as const,
                label: "Open in a new tab",
                hint: "Recommended for external applications.",
              },
            ].map((option) => (
              <div key={option.key} className="flex items-start justify-between gap-4">
                <div>
                  <Label htmlFor={`project-${option.key}`}>{option.label}</Label>
                  <p className="text-xs text-muted-foreground">{option.hint}</p>
                </div>
                <Switch
                  id={`project-${option.key}`}
                  checked={values[option.key]}
                  onCheckedChange={(checked) => set(option.key, checked)}
                />
              </div>
            ))}

            <div className="flex items-center justify-between gap-4">
              <div>
                <Label htmlFor="project-sort">Sort order</Label>
                <p className="text-xs text-muted-foreground">Lower numbers appear first.</p>
              </div>
              <Input
                id="project-sort"
                type="number"
                value={values.sort_order}
                onChange={(event) => set("sort_order", Number(event.target.value) || 0)}
                className="w-24"
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              {!create.isPending && !update.isPending && <Plus />}
              {isEdit ? "Save changes" : "Add project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
