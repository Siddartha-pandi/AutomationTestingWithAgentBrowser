"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Shield, KeyRound, Mail, ArrowRight, AlertCircle, Building, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/common/ToastProvider";
import { BrowserAutomationLogo } from "@/components/common/BrowserLogo";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const { success, error: toastError } = useToast();

  const [fullName, setFullName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await register(email, password);
      success("Workspace created", "Your account has been provisioned successfully.");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed. Please review your details.");
      toastError("Registration failed", err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center p-6 bg-gradient-to-b from-[#0B0F17] via-[#0F172A] to-[#0B0F17]">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center space-y-2">
          <BrowserAutomationLogo size={52} className="mx-auto mb-2" />
          <h1 className="text-2xl font-bold text-white tracking-tight">Create Workspace Account</h1>
          <p className="text-sm text-slate-400">
            Set up an isolated enterprise tenant for browser testing and automation
          </p>
        </div>

        <div className="bg-[#161F30] border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-5">
          {error && (
            <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Alex Morgan"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Workspace Name
                </label>
                <div className="relative">
                  <Building className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    value={workspaceName}
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    placeholder="Acme QA Suite"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Corporate Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex.morgan@company.internal"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Password
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
                />
              </div>
            </div>

            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-300 flex items-start gap-2">
              <Shield className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <span>
                By creating a workspace, you confirm compliance with your organization's Zero-AI policy. No data or DOM content will ever be transmitted to external AI endpoints.
              </span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#2563EB] hover:bg-blue-600 disabled:opacity-50 text-white font-medium rounded-xl shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2 text-sm mt-2"
            >
              {loading ? (
                <span>Provisioning Tenant...</span>
              ) : (
                <>
                  <span>Create Workspace & Start Testing</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="text-center text-xs text-slate-400">
            Already have an enterprise account?{" "}
            <Link href="/login" className="text-blue-400 hover:underline font-medium">
              Sign In here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
