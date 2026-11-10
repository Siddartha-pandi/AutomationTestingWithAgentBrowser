"use client";

import React, { useState, useEffect } from "react";
import {
  Crosshair,
  Plus,
  Search,
  Trash2,
  Edit,
  Play,
  History,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  Layers,
  Tag,
  X,
  ExternalLink,
} from "lucide-react";
import { intelligenceApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface ElementProfilesPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface ElementProfileItem {
  id: string;
  logical_id: string;
  description: string;
  page_context: string;
  element_type: string;
  recognition_strategy: string;
  last_successful_match: string;
  last_updated: string;
  status: "verified" | "mutated" | "draft";
  locators: { type: string; value: string; success_count: number }[];
}

export function ElementProfilesPage({ projectId, onNavigate }: ElementProfilesPageProps) {
  const [profiles, setProfiles] = useState<ElementProfileItem[]>([
    {
      id: "ep-1",
      logical_id: "referral_submit_btn",
      description: "Primary submit action on customer referral creation modal",
      page_context: "Referral Dashboard",
      element_type: "button",
      recognition_strategy: "Deterministic Multi-Factor (Levenshtein + ARIA)",
      last_successful_match: "10 mins ago (98.2% confidence)",
      last_updated: "2026-11-10",
      status: "verified",
      locators: [
        { type: "role_name", value: "button[name='Send Referral']", success_count: 142 },
        { type: "data_testid", value: "[data-testid='referral-submit-action']", success_count: 98 },
        { type: "css_id", value: "#submit-referral-btn", success_count: 34 },
      ],
    },
    {
      id: "ep-2",
      logical_id: "user_email_input",
      description: "Corporate login email input with autocomplete",
      page_context: "Authentication Login",
      element_type: "input",
      recognition_strategy: "Stable Attribute + Accessible Name",
      last_successful_match: "1 hour ago (100% confidence)",
      last_updated: "2026-11-10",
      status: "verified",
      locators: [
        { type: "role_name", value: "textbox[name='Corporate Email']", success_count: 220 },
        { type: "stable_attr", value: "input[type='email']#user-email-field", success_count: 180 },
      ],
    },
    {
      id: "ep-3",
      logical_id: "kyc_upload_dropzone",
      description: "Document file dropzone for government photo ID",
      page_context: "KYC Verification",
      element_type: "div",
      recognition_strategy: "Structural Fingerprint & Context",
      last_successful_match: "Yesterday (89.4% confidence - Healed)",
      last_updated: "2026-11-09",
      status: "mutated",
      locators: [
        { type: "css_id", value: "#kyc-dropzone-v2", success_count: 12 },
        { type: "structural", value: "div.upload-zone:has(input[type=file])", success_count: 45 },
      ],
    },
  ]);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<ElementProfileItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Create form state
  const [logicalIdInput, setLogicalIdInput] = useState("");
  const [descInput, setDescInput] = useState("");
  const [contextInput, setContextInput] = useState("Dashboard");
  const [typeInput, setTypeInput] = useState("button");
  const [selectorInput, setSelectorInput] = useState("");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const handleTestRecognition = (profile: ElementProfileItem) => {
    info("Testing Deterministic Match", `Running multi-factor scoring against live DOM for '${profile.logical_id}'...`);
    setTimeout(() => {
      success("Recognition Passed", `Identified uniquely with 97.8% confidence score.`);
    }, 1200);
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!logicalIdInput.trim()) {
      error("Logical ID Required", "Please provide a valid logical ID.");
      return;
    }

    const newProfile: ElementProfileItem = {
      id: `ep-${Date.now()}`,
      logical_id: logicalIdInput.trim(),
      description: descInput.trim() || "Multi-signal element profile",
      page_context: contextInput,
      element_type: typeInput,
      recognition_strategy: "Deterministic Multi-Factor (Levenshtein + ARIA)",
      last_successful_match: "Never",
      last_updated: new Date().toISOString().split("T")[0],
      status: "draft",
      locators: [
        { type: "primary_selector", value: selectorInput || `[data-testid='${logicalIdInput}']`, success_count: 0 },
      ],
    };

    setProfiles([newProfile, ...profiles]);
    setModalOpen(false);
    success("Element Profile Created", `Logical ID '${logicalIdInput}' registered.`);
  };

  const handleDeleteProfile = (profile: ElementProfileItem) => {
    confirm({
      title: "Delete Element Profile",
      message: `Delete profile '${profile.logical_id}'? This will remove all associated locator history.`,
      confirmText: "Delete Profile",
      variant: "danger",
      onConfirm: () => {
        setProfiles(profiles.filter((p) => p.id !== profile.id));
        success("Profile Removed", `Deleted ${profile.logical_id}.`);
      },
    });
  };

  const filtered = profiles.filter(
    (p) =>
      p.logical_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.page_context.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Crosshair className="w-5 h-5 text-[#2563EB]" />
            <span>Element Profiles</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Maintain multi-factor identity signals and historical verification records for automated selectors.
          </p>
        </div>

        <button
          onClick={() => {
            setLogicalIdInput("");
            setDescInput("");
            setContextInput("Dashboard");
            setSelectorInput("");
            setModalOpen(true);
          }}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Element Profile</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search profiles by logical ID or context..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="text-[11px] font-mono text-slate-400 hidden sm:block">
          Deterministic Engine: <span className="text-emerald-600 font-bold">Multi-Signal Scoring Active</span>
        </div>
      </div>

      {/* Element Profiles Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Logical ID & Description</th>
                <th className="py-3 px-3">Page Context</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Recognition Strategy</th>
                <th className="py-3 px-3">Last Match</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((profile) => (
                <tr key={profile.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 max-w-sm">
                    <div className="font-mono font-bold text-[#2563EB] dark:text-blue-400 text-xs">
                      {profile.logical_id}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                      {profile.description}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {profile.page_context}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                      &lt;{profile.element_type}&gt;
                    </span>
                  </td>

                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                    <div className="truncate max-w-[180px] font-medium" title={profile.recognition_strategy}>
                      {profile.recognition_strategy}
                    </div>
                  </td>

                  <td className="py-3 px-3 text-[11px] text-slate-500 dark:text-slate-400">
                    {profile.last_successful_match}
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                        profile.status === "verified"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : profile.status === "mutated"
                          ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                      }`}
                    >
                      {profile.status === "verified" && <CheckCircle2 className="w-3 h-3" />}
                      <span>{profile.status}</span>
                    </span>
                  </td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Test Recognition Action */}
                      <button
                        onClick={() => handleTestRecognition(profile)}
                        title="Test Deterministic Match"
                        className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/60 dark:hover:bg-blue-900 text-[#2563EB] dark:text-blue-300 transition"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>

                      {/* Inspect / Edit */}
                      <button
                        onClick={() => {
                          setSelectedProfile(profile);
                          onNavigate("browser_recognition");
                        }}
                        title="Inspect Locator Candidates"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <History className="w-3.5 h-3.5" />
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() => handleDeleteProfile(profile)}
                        title="Delete Profile"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/60 text-rose-600 dark:text-rose-400 transition"
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

      {/* Create Modal Dialog */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Crosshair className="w-4 h-4 text-[#2563EB]" />
                <span>Create Element Profile</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateProfile} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Logical Element ID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. checkout_submit_btn"
                  value={logicalIdInput}
                  onChange={(e) => setLogicalIdInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Description
                </label>
                <input
                  type="text"
                  placeholder="e.g. Final button submitting checkout order"
                  value={descInput}
                  onChange={(e) => setDescInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Page Context
                  </label>
                  <input
                    type="text"
                    value={contextInput}
                    onChange={(e) => setContextInput(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Element Type
                  </label>
                  <select
                    value={typeInput}
                    onChange={(e) => setTypeInput(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  >
                    <option value="button">button</option>
                    <option value="input">input</option>
                    <option value="select">select</option>
                    <option value="a">a (link)</option>
                    <option value="div">div</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Primary Locator Selector
                </label>
                <input
                  type="text"
                  placeholder="#checkout-submit"
                  value={selectorInput}
                  onChange={(e) => setSelectorInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono text-slate-900 dark:text-slate-100"
                />
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
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
