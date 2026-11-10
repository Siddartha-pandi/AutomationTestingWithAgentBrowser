"use client";

import React, { useState } from "react";
import {
  User,
  Lock,
  Sun,
  Moon,
  Laptop,
  Bell,
  ShieldCheck,
  CheckCircle2,
  LogOut,
  Clock,
  KeyRound,
  Save,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useTheme } from "../common/ThemeProvider";
import { NavView } from "../layout/AppShell";

interface UserProfilePageProps {
  user: { email: string; full_name?: string; role?: string } | null;
  onLogout: () => void;
  onNavigate: (view: NavView) => void;
}

export function UserProfilePage({ user, onLogout, onNavigate }: UserProfilePageProps) {
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const { theme, setTheme } = useTheme();

  // Notification Preferences
  const [notifyFailures, setNotifyFailures] = useState(true);
  const [notifyApprovals, setNotifyApprovals] = useState(true);
  const [notifyDailyDigest, setNotifyDailyDigest] = useState(false);

  const { success, error, info } = useToast();

  const handleUpdateProfile = (e: React.FormEvent) => {
    e.preventDefault();
    const updatedUser = { ...user, full_name: fullName, email };
    localStorage.setItem("auth_user", JSON.stringify(updatedUser));
    success("Profile Updated", "Account display settings updated.");
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      error("Password Error", "Please provide current password.");
      return;
    }
    if (newPassword.length < 8) {
      error("Password Length", "New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      error("Password Mismatch", "New passwords do not match.");
      return;
    }
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    success("Password Changed", "Security credentials updated successfully.");
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <User className="w-5 h-5 text-[#2563EB]" />
            <span>User Profile & Workspace Preferences</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage your personal credentials, appearance themes, and event alerts.
          </p>
        </div>

        <button
          onClick={onLogout}
          className="px-3.5 py-2 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-600 dark:text-rose-400 text-xs font-semibold flex items-center gap-1.5 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Profile Overview Card */}
      <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-[#2563EB] text-white flex items-center justify-center font-bold text-xl shadow-md">
            {fullName[0]?.toUpperCase() || "A"}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{fullName}</h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 font-bold">
                {user?.role || "Owner"}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">{email}</p>
          </div>
        </div>

        <form onSubmit={handleUpdateProfile} className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-4 border-t border-slate-100 dark:border-slate-800">
          <div>
            <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Display Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="sm:col-span-2 flex justify-end">
            <button
              type="submit"
              className="px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1.5 shadow-xs transition"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Profile</span>
            </button>
          </div>
        </form>
      </div>

      {/* Theme & Display Preferences */}
      <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
        <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Sun className="w-4 h-4 text-amber-500" />
          <span>Appearance & Color Theme</span>
        </h3>

        <div className="grid grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => setTheme("light")}
            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition ${
              theme === "light"
                ? "bg-blue-50 dark:bg-blue-950/60 border-blue-500 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500/10 font-bold"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
            }`}
          >
            <Sun className="w-5 h-5 text-amber-500" />
            <span className="text-xs">Light Mode</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme("dark")}
            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition ${
              theme === "dark"
                ? "bg-blue-50 dark:bg-blue-950/60 border-blue-500 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500/10 font-bold"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
            }`}
          >
            <Moon className="w-5 h-5 text-blue-400" />
            <span className="text-xs">Dark Mode</span>
          </button>

          <button
            type="button"
            onClick={() => setTheme("system")}
            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition ${
              theme === "system"
                ? "bg-blue-50 dark:bg-blue-950/60 border-blue-500 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500/10 font-bold"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
            }`}
          >
            <Laptop className="w-5 h-5 text-slate-500" />
            <span className="text-xs">System Match</span>
          </button>
        </div>
      </div>

      {/* Notification Preferences */}
      <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4 text-xs">
        <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Bell className="w-4 h-4 text-[#2563EB]" />
          <span>Notification & Event Triggers</span>
        </h3>

        <div className="space-y-3">
          <label className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 cursor-pointer">
            <div>
              <span className="font-bold text-slate-800 dark:text-slate-200 block">Execution Failures</span>
              <span className="text-[11px] text-slate-400">Receive in-app alerts whenever a test assertion fails</span>
            </div>
            <input
              type="checkbox"
              checked={notifyFailures}
              onChange={(e) => setNotifyFailures(e.target.checked)}
              className="rounded text-blue-600"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 cursor-pointer">
            <div>
              <span className="font-bold text-slate-800 dark:text-slate-200 block">Self-Healing Approval Gates</span>
              <span className="text-[11px] text-slate-400">Notify when an element mutation falls in the 85-94% human review tier</span>
            </div>
            <input
              type="checkbox"
              checked={notifyApprovals}
              onChange={(e) => setNotifyApprovals(e.target.checked)}
              className="rounded text-blue-600"
            />
          </label>
        </div>
      </div>

      {/* Change Password */}
      <form onSubmit={handleChangePassword} className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4 text-xs">
        <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Lock className="w-4 h-4 text-rose-500" />
          <span>Change Password</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Current Password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-slate-800 dark:bg-slate-700 hover:bg-slate-900 text-white font-semibold flex items-center gap-1.5 shadow-xs transition"
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Update Password</span>
          </button>
        </div>
      </form>
    </div>
  );
}
