"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  Plus,
  Search,
  CheckCircle2,
  Trash2,
  Edit,
  UserPlus,
  ShieldCheck,
  Mail,
  X,
  Lock,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";
import { adminApi } from "@/api";

interface UsersManagementPageProps {
  onNavigate: (view: NavView) => void;
}

interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: "Owner" | "Admin" | "Developer" | "Tester" | "Viewer";
  status: "active" | "inactive";
  last_login: string;
  created_at: string;
}

export function UsersManagementPage({ onNavigate }: UsersManagementPageProps) {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const list = await adminApi.listUsers();
      if (list && list.length > 0) {
        setUsers(
          list.map((u: any) => ({
            id: String(u.id),
            name: u.full_name || u.email.split("@")[0],
            email: u.email,
            role: (u.roles && u.roles[0]?.name
              ? (u.roles[0].name.charAt(0).toUpperCase() + u.roles[0].name.slice(1))
              : "Viewer") as any,
            status: u.is_active ? "active" : "inactive",
            last_login: "Recent",
            created_at: u.created_at ? u.created_at.split("T")[0] : new Date().toISOString().split("T")[0],
          }))
        );
      } else {
        setUsers([]);
      }
    } catch {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const [modalOpen, setModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [roleInput, setRoleInput] = useState<"Admin" | "Developer" | "Tester" | "Viewer">("Developer");

  const { success, info } = useToast();
  const { confirm } = useConfirm();

  const handleInviteUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput.trim()) return;

    const newUser: UserAccount = {
      id: `u-${Date.now()}`,
      name: nameInput.trim() || emailInput.split("@")[0],
      email: emailInput.trim(),
      role: roleInput,
      status: "active",
      last_login: "Never",
      created_at: new Date().toISOString().split("T")[0],
    };

    setUsers([...users, newUser]);
    setModalOpen(false);
    success("Invitation Sent", `Invited '${emailInput}' with role '${roleInput}'.`);
  };

  const handleToggleStatus = (user: UserAccount) => {
    if (user.role === "Owner") {
      info("Protected Account", "The primary Owner role cannot be deactivated.");
      return;
    }
    setUsers(
      users.map((u) =>
        u.id === user.id ? { ...u, status: u.status === "active" ? "inactive" : "active" } : u
      )
    );
    success(
      "Status Updated",
      `User '${user.name}' is now ${user.status === "active" ? "inactive" : "active"}.`
    );
  };

  const handleDeleteUser = (user: UserAccount) => {
    if (user.role === "Owner") {
      info("Protected Account", "Owner account cannot be deleted.");
      return;
    }
    confirm({
      title: "Remove User",
      message: `Revoke platform access for '${user.email}'?`,
      confirmText: "Revoke Access",
      variant: "danger",
      onConfirm: () => {
        setUsers(users.filter((u) => u.id !== user.id));
        success("Access Revoked", `User '${user.email}' removed.`);
      },
    });
  };

  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-[#2563EB]" />
            <span>User Management</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Administer multi-user enterprise access, role assignments, and account statuses.
          </p>
        </div>

        <button
          onClick={() => {
            setNameInput("");
            setEmailInput("");
            setRoleInput("Developer");
            setModalOpen(true);
          }}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite New User</span>
        </button>
      </div>

      {/* Search Toolbar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search users by name, email or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>
        <span className="text-[11px] font-mono text-slate-400">{filtered.length} registered accounts</span>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">User & Email</th>
                <th className="py-3 px-3">Role</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Last Login</th>
                <th className="py-3 px-3">Created Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#2563EB] text-white flex items-center justify-center font-bold text-xs shrink-0">
                        {user.name[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                          {user.name}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">{user.email}</div>
                      </div>
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                        user.role === "Owner"
                          ? "bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 font-bold"
                          : user.role === "Admin"
                          ? "bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {user.role}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <button
                      onClick={() => handleToggleStatus(user)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                        user.status === "active"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-400 border border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      {user.status}
                    </button>
                  </td>

                  <td className="py-3 px-3 text-slate-500">{user.last_login}</td>

                  <td className="py-3 px-3 text-slate-400 text-[11px]">{user.created_at}</td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleDeleteUser(user)}
                        disabled={user.role === "Owner"}
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 transition disabled:opacity-30"
                        title="Delete User"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-[#2563EB]" />
                <span>Invite New Platform Member</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleInviteUser} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Full Name</label>
                <input
                  type="text"
                  placeholder="Jane Doe"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Corporate Email *</label>
                <input
                  type="email"
                  required
                  placeholder="jane.doe@company.internal"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Assigned Role</label>
                <select
                  value={roleInput}
                  onChange={(e) => setRoleInput(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value="Admin">Admin (Configuration & User Mgmt)</option>
                  <option value="Developer">Developer (Author Flows & Tests)</option>
                  <option value="Tester">Tester (Run & View Reports)</option>
                  <option value="Viewer">Viewer (Read-Only Audit)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold shadow-xs"
                >
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
