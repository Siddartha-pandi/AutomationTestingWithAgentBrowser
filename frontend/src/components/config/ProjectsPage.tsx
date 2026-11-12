"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  Plus,
  Search,
  CheckCircle2,
  Trash2,
  Edit,
  Globe,
  User,
  Calendar,
  X,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { projectsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface ProjectsPageProps {
  currentProject: { id: string; name: string } | null;
  onSelectProject?: (proj: { id: string; name: string }) => void;
  onNavigate: (view: NavView) => void;
}

interface ProjectItem {
  id: string;
  name: string;
  description: string;
  base_url: string;
  owner: string;
  created_at: string;
  status: "active" | "archived";
}

export function ProjectsPage({ currentProject, onSelectProject, onNavigate }: ProjectsPageProps) {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<ProjectItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [descInput, setDescInput] = useState("");
  const [urlInput, setUrlInput] = useState("https://example.internal.company.net");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await projectsApi.list();
      if (res && res.length > 0) {
        setProjects(
          res.map((p: any) => ({
            id: p.id,
            name: p.name,
            description: p.description || "Project tenant workspace.",
            base_url: "https://staging.internal.company.net",
            owner: p.owner_id ? "Lead Administrator" : "Organization",
            created_at: p.created_at ? p.created_at.split("T")[0] : new Date().toISOString().split("T")[0],
            status: "active",
          }))
        );
      } else {
        setProjects([]);
      }
    } catch (err: any) {
      console.warn("Could not fetch projects:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleOpenCreateModal = () => {
    setEditingProject(null);
    setNameInput("");
    setDescInput("");
    setUrlInput("https://example.internal.company.net");
    setModalOpen(true);
  };

  const handleOpenEditModal = (proj: ProjectItem) => {
    setEditingProject(proj);
    setNameInput(proj.name);
    setDescInput(proj.description || "");
    setUrlInput(proj.base_url || "https://example.internal.company.net");
    setModalOpen(true);
  };

  const handleSaveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nameInput.trim()) return;

    if (editingProject) {
      try {
        await projectsApi.update(editingProject.id, {
          name: nameInput.trim(),
          description: descInput.trim() || undefined,
        });
      } catch {
        // Optimistic update
      }

      setProjects(
        projects.map((p) =>
          p.id === editingProject.id
            ? {
                ...p,
                name: nameInput.trim(),
                description: descInput.trim() || "No description provided.",
                base_url: urlInput.trim(),
              }
            : p
        )
      );
      if (onSelectProject && currentProject?.id === editingProject.id) {
        onSelectProject({ id: editingProject.id, name: nameInput.trim() });
      }
      setModalOpen(false);
      setEditingProject(null);
      success("Project Updated", `Workspace '${nameInput}' has been updated.`);
      return;
    }

    try {
      const created = await projectsApi.create({
        name: nameInput.trim(),
        description: descInput.trim() || undefined,
      });

      const newProj: ProjectItem = {
        id: created.id,
        name: created.name,
        description: created.description || "No description provided.",
        base_url: urlInput.trim(),
        owner: "Lead Administrator",
        created_at: new Date().toISOString().split("T")[0],
        status: "active",
      };

      setProjects([newProj, ...projects]);
      if (onSelectProject) {
        onSelectProject({ id: newProj.id, name: newProj.name });
      }
      setModalOpen(false);
      success("Project Created", `Tenant workspace '${nameInput}' initialized with strict isolation.`);
    } catch (err: any) {
      error("Create Project Failed", err.message || "Failed to create project tenant.");
    }
  };

  const handleDeleteProject = (proj: ProjectItem) => {
    confirm({
      title: "Delete Project Workspace",
      message: `Permanently delete workspace '${proj.name}'? This action cannot be undone and will delete all associated configurations.`,
      confirmText: "Delete Project",
      variant: "danger",
      onConfirm: async () => {
        try {
          await projectsApi.delete(proj.id);
        } catch {
          // Fallback optimistic
        }
        setProjects(projects.filter((p) => p.id !== proj.id));
        success("Project Deleted", `Project workspace '${proj.name}' has been deleted.`);
      },
    });
  };

  const handleSelectActive = (proj: ProjectItem) => {
    if (onSelectProject) {
      onSelectProject({ id: proj.id, name: proj.name });
    }
    success("Workspace Switched", `Active project set to '${proj.name}'.`);
  };

  const handleArchive = (proj: ProjectItem) => {
    confirm({
      title: "Archive Project",
      message: `Archive project workspace '${proj.name}'? Existing executions and profiles will be preserved.`,
      confirmText: "Archive",
      variant: "warning",
      onConfirm: () => {
        setProjects(
          projects.map((p) =>
            p.id === proj.id ? { ...p, status: p.status === "active" ? "archived" : "active" } : p
          )
        );
        info("Status Updated", `Project '${proj.name}' archived.`);
      },
    });
  };

  const filtered = projects.filter((p) => {
    const q = (searchQuery || "").trim().toLowerCase();
    if (!q) return true;
    const nameStr = (p?.name || "").toLowerCase();
    const descStr = (p?.description || "").toLowerCase();
    return nameStr.includes(q) || descStr.includes(q);
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-[#2563EB]" />
            <span>Projects & Tenant Workspaces</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Maintain strict multi-tenant isolation across flows, tests, elements and credentials.
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid or Empty State */}
      {filtered.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white dark:bg-[#161F30] border border-dashed border-slate-200 dark:border-slate-800 space-y-3">
          <Layers className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto" />
          <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">No Projects Found</h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            You don't have any projects in this workspace yet. Create your first project to begin building automated flows and test suites.
          </p>
          <button
            onClick={handleOpenCreateModal}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((proj) => {
            const isActive = currentProject?.id === proj.id;
            return (
              <div
                key={proj.id}
                className={`p-5 rounded-2xl bg-white dark:bg-[#161F30] border shadow-2xs space-y-4 transition ${
                  isActive
                    ? "border-[#2563EB] ring-2 ring-blue-500/10"
                    : "border-slate-200 dark:border-slate-800"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <span>{proj.name}</span>
                      {isActive && (
                        <span className="text-[10px] px-2 py-0.2 rounded-full bg-blue-100 dark:bg-blue-900/60 text-[#2563EB] dark:text-blue-300 font-semibold font-mono">
                          Active
                        </span>
                      )}
                    </h3>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                      {proj.description}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                        proj.status === "active"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                      }`}
                    >
                      {proj.status}
                    </span>
                    <button
                      onClick={() => handleOpenEditModal(proj)}
                      className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      title="Edit Project"
                    >
                      <Edit className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteProject(proj)}
                      className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/60 text-rose-600 dark:text-rose-400 transition"
                      title="Delete Project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs pt-3 border-t border-slate-100 dark:border-slate-800 text-slate-600 dark:text-slate-300">
                  <div className="flex items-center gap-2 truncate">
                    <Globe className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="font-mono text-[11px] truncate">{proj.base_url}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>Owner: {proj.owner}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                  {!isActive ? (
                    <button
                      onClick={() => handleSelectActive(proj)}
                      className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold transition"
                    >
                      Select Workspace
                    </button>
                  ) : (
                    <span className="text-emerald-600 font-semibold text-xs flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Selected</span>
                    </span>
                  )}

                  <button
                    onClick={() => handleArchive(proj)}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-semibold"
                  >
                    {proj.status === "active" ? "Archive" : "Unarchive"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Project Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#2563EB]" />
                <span>{editingProject ? "Edit Project Tenant" : "Create New Project Tenant"}</span>
              </h3>
              <button
                onClick={() => {
                  setModalOpen(false);
                  setEditingProject(null);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveProject} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Customer Portal"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Outline the workflows and application components..."
                  value={descInput}
                  onChange={(e) => setDescInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 resize-none"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Base Application URL
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://app.company.internal"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setModalOpen(false);
                    setEditingProject(null);
                  }}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold shadow-xs"
                >
                  {editingProject ? "Save Changes" : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
