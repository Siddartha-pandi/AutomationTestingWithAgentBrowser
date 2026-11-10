"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (toast: Omit<ToastItem, "id">) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    ({ type, title, message, duration = 4000 }: Omit<ToastItem, "id">) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      setToasts((prev) => [...prev, { id, type, title, message, duration }]);
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  const success = useCallback((title: string, message?: string) => showToast({ type: "success", title, message }), [showToast]);
  const error = useCallback((title: string, message?: string) => showToast({ type: "error", title, message }), [showToast]);
  const warning = useCallback((title: string, message?: string) => showToast({ type: "warning", title, message }), [showToast]);
  const info = useCallback((title: string, message?: string) => showToast({ type: "info", title, message }), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => {
          const bgBorder =
            t.type === "success"
              ? "bg-white dark:bg-slate-900 border-emerald-500 text-slate-800 dark:text-slate-100 shadow-emerald-500/10"
              : t.type === "error"
              ? "bg-white dark:bg-slate-900 border-rose-500 text-slate-800 dark:text-slate-100 shadow-rose-500/10"
              : t.type === "warning"
              ? "bg-white dark:bg-slate-900 border-amber-500 text-slate-800 dark:text-slate-100 shadow-amber-500/10"
              : "bg-white dark:bg-slate-900 border-blue-500 text-slate-800 dark:text-slate-100 shadow-blue-500/10";

          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border-l-4 border shadow-lg transition-all transform duration-200 animate-in fade-in slide-in-from-bottom-2 ${bgBorder}`}
            >
              <div className="shrink-0 mt-0.5">
                {t.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                {t.type === "error" && <XCircle className="w-4 h-4 text-rose-600" />}
                {t.type === "warning" && <AlertTriangle className="w-4 h-4 text-amber-600" />}
                {t.type === "info" && <Info className="w-4 h-4 text-blue-600" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold leading-tight">{t.title}</p>
                {t.message && <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">{t.message}</p>}
              </div>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded transition"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
