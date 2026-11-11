/**
 * Enterprise API client for AutomationTestingWithAgentBrowser.
 *
 * Communicates with FastAPI backend (/api/v1/...) using JWT tokens, HTTP-only cookie support,
 * and standard REST schemas.
 * Strictly Zero-AI / No-LLM data handling.
 */

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const url = `${API_BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (err) {
    throw new Error(
      `Cannot connect to backend server at ${API_BASE_URL}. Please ensure the FastAPI backend is running.`
    );
  }

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      window.dispatchEvent(new Event("auth:unauthorized"));
    }
    let detail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && typeof errJson.detail === "string") {
        detail = errJson.detail;
      } else if (errJson && errJson.detail) {
        detail = JSON.stringify(errJson.detail);
      }
    } catch {
      // response is not json
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

// 1. Authentication
export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; user: any }>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  register: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; user: any }>("/api/v1/auth/register", {
      method: "POST",
      body: { email, password },
    }),
  me: () => request<any>("/api/v1/auth/me"),
};

// 2. Flows (Workflows)
export const flowsApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/flows${projectId ? `?project_id=${projectId}` : ""}`),
  get: (id: string) => request<any>(`/api/v1/flows/${id}`),
  getTemplates: () => request<any[]>("/api/v1/flows/templates"),
  create: (data: { project_id: string; name: string; description?: string; definition?: any; flow_graph?: any }) =>
    request<any>("/api/v1/flows", { method: "POST", body: { ...data, definition: data.definition || data.flow_graph } }),
  update: (id: string, data: { name?: string; description?: string; definition?: any; flow_graph?: any }) =>
    request<any>(`/api/v1/flows/${id}`, { method: "PUT", body: { ...data, definition: data.definition || data.flow_graph } }),
  publish: (id: string) => request<any>(`/api/v1/flows/${id}/publish`, { method: "POST" }),
  validate: (definition: any) =>
    request<any>("/api/v1/flows/validate", { method: "POST", body: { definition } }),
  execute: (id: string, data?: { version_id?: string; initial_variables?: Record<string, any> }) =>
    request<any>(`/api/v1/flows/${id}/execute`, { method: "POST", body: data || {} }),
};

// 3. Tests & Suites
export const testsApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/tests${projectId ? `?project_id=${projectId}` : ""}`),
  get: (id: string) => request<any>(`/api/v1/tests/${id}`),
  create: (data: { project_id: string; name: string; description?: string; test_case: any }) =>
    request<any>("/api/v1/tests", { method: "POST", body: data }),
  update: (id: string, data: { name?: string; description?: string; test_case?: any }) =>
    request<any>(`/api/v1/tests/${id}`, { method: "PUT", body: data }),
  publish: (id: string) => request<any>(`/api/v1/tests/${id}/publish`, { method: "POST" }),
  execute: (id: string, data?: { test_data_row?: Record<string, any> }) =>
    request<any>(`/api/v1/tests/${id}/execute`, { method: "POST", body: data || {} }),
  seedLegacy: (projectId: string) =>
    request<any[]>("/api/v1/tests/seed-legacy", { method: "POST", body: { project_id: projectId } }),
  listDatasets: (projectId?: string) =>
    request<any[]>(`/api/v1/tests/datasets${projectId ? `?project_id=${projectId}` : ""}`),
  createDataset: (data: { project_id: string; name: string; description?: string; format?: string; headers: string[]; rows: any[] }) =>
    request<any>("/api/v1/tests/datasets", { method: "POST", body: data }),
  deleteDataset: (id: string) =>
    request<void>(`/api/v1/tests/datasets/${id}`, { method: "DELETE" }),
};

export const testSuitesApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/test-suites${projectId ? `?project_id=${projectId}` : ""}`),
  get: (id: string) => request<any>(`/api/v1/test-suites/${id}`),
  create: (data: { project_id: string; name: string; description?: string; test_suite: any }) =>
    request<any>("/api/v1/test-suites", { method: "POST", body: data }),
  execute: (id: string) =>
    request<any>(`/api/v1/test-suites/${id}/execute`, { method: "POST", body: {} }),
};

// 4. Executions & Reports
export const executionsApi = {
  list: (filters?: { status?: string; projectId?: string }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.append("status", filters.status);
    if (filters?.projectId) params.append("project_id", filters.projectId);
    const qs = params.toString();
    return request<any[]>(`/api/v1/executions${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => request<any>(`/api/v1/executions/${id}`),
  cancel: (id: string) => request<any>(`/api/v1/executions/${id}/cancel`, { method: "POST" }),
  getReport: (id: string) => request<any>(`/api/v1/executions/${id}/report`),
  getLogs: (id: string, filters?: { level?: string; search?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (filters?.level) params.append("level", filters.level);
    if (filters?.search) params.append("search", filters.search);
    if (filters?.limit) params.append("limit", String(filters.limit));
    if (filters?.offset) params.append("offset", String(filters.offset));
    const qs = params.toString();
    return request<any>(`/api/v1/executions/${id}/logs${qs ? `?${qs}` : ""}`);
  },
  getHtmlReportUrl: (id: string) => `${API_BASE_URL}/api/v1/executions/${id}/report/html`,
  getLogsDownloadUrl: (id: string, format: "txt" | "json" = "txt", level?: string) =>
    `${API_BASE_URL}/api/v1/executions/${id}/logs/download?format=${format}${level ? `&level=${level}` : ""}`,
  getViewportUrl: (id: string) => `${API_BASE_URL}/api/v1/executions/${id}/viewport`,
};

// 5. DOM & Intelligence
export const intelligenceApi = {
  extractDom: (sessionId: string, selector?: string) =>
    request<any>("/api/v1/dom/extract", { method: "POST", body: { session_id: sessionId, selector } }),
  listElements: (projectId: string) =>
    request<any[]>(`/api/v1/elements?project_id=${projectId}`),
  createElement: (data: any) =>
    request<any>("/api/v1/elements", { method: "POST", body: data }),
  getElement: (id: string) =>
    request<any>(`/api/v1/elements/${id}`),
  listHealingEvents: () =>
    request<any[]>("/api/v1/healing/events"),
  listApprovals: (statusFilter?: string) =>
    request<any[]>(`/api/v1/healing/approvals${statusFilter ? `?status=${statusFilter}` : ""}`),
  respondApproval: (id: string, decision: "approved" | "rejected", comment?: string) =>
    request<any>(`/api/v1/healing/approvals/${id}/respond`, {
      method: "POST",
      body: { decision, comment },
    }),
};

// 6. Projects, Environments & Credentials
export const projectsApi = {
  list: () => request<any[]>("/api/v1/projects"),
  get: (id: string) => request<any>(`/api/v1/projects/${id}`),
  create: (data: { name: string; description?: string }) =>
    request<any>("/api/v1/projects", { method: "POST", body: data }),
  listMembers: (projectId: string) =>
    request<any[]>(`/api/v1/projects/${projectId}/members`),
  addMember: (projectId: string, data: { user_id: string; role: string }) =>
    request<any>(`/api/v1/projects/${projectId}/members`, { method: "POST", body: data }),
  removeMember: (projectId: string, userId: string) =>
    request<void>(`/api/v1/projects/${projectId}/members/${userId}`, { method: "DELETE" }),
};

export const environmentsApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/environments${projectId ? `?project_id=${projectId}` : ""}`),
  get: (id: string) =>
    request<any>(`/api/v1/environments/${id}`),
  create: (data: { project_id: string; name: string; base_url: string; allowed_domains?: string[]; variables?: Record<string, string> }) =>
    request<any>("/api/v1/environments", { method: "POST", body: data }),
  update: (id: string, data: { name?: string; base_url?: string; allowed_domains?: string[]; variables?: Record<string, string> }) =>
    request<any>(`/api/v1/environments/${id}`, { method: "PUT", body: data }),
  delete: (id: string) =>
    request<void>(`/api/v1/environments/${id}`, { method: "DELETE" }),
};

export const credentialsApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/credentials${projectId ? `?project_id=${projectId}` : ""}`),
  get: (id: string) =>
    request<any>(`/api/v1/credentials/${id}`),
  create: (data: { project_id: string; name: string; credential_type: string; username?: string; secret_value: string; domain_scope?: string }) =>
    request<any>("/api/v1/credentials", { method: "POST", body: data }),
  update: (id: string, data: { name?: string; credential_type?: string; username?: string; secret_value?: string; domain_scope?: string }) =>
    request<any>(`/api/v1/credentials/${id}`, { method: "PUT", body: data }),
  delete: (id: string) =>
    request<void>(`/api/v1/credentials/${id}`, { method: "DELETE" }),
};

// 7. Browser Engine & Interactive Sessions
export const browserApi = {
  getStatus: () => request<any>("/api/v1/browser/status"),
  testConnection: () => request<any>("/api/v1/browser/test-connection", { method: "POST" }),
  launch: (data?: { project_id?: string; session_id?: string; allowed_domains?: string[] }) =>
    request<any>("/api/v1/browser/launch", { method: "POST", body: data || {} }),
  navigate: (sessionId: string, url: string, timeout = 30) =>
    request<any>("/api/v1/browser/navigate", { method: "POST", body: { session_id: sessionId, url, timeout } }),
  action: (sessionId: string, data: { action: string; selector?: string; text?: string; value?: string; timeout?: number }) =>
    request<any>("/api/v1/browser/action", { method: "POST", body: { session_id: sessionId, ...data } }),
  screenshot: (sessionId: string, data?: { custom_name?: string; full_page?: boolean }) =>
    request<any>("/api/v1/browser/screenshot", { method: "POST", body: { session_id: sessionId, ...data } }),
  getViewport: (sessionId: string) =>
    request<any>(`/api/v1/browser/viewport/${sessionId}`),
  validateSelector: (selector: string) =>
    request<any>("/api/v1/browser/validate-selector", { method: "POST", body: { selector } }),
  testSelector: (data: { session_id: string; selector: string; fallbacks?: string[]; highlight?: boolean; timeout?: number }) =>
    request<any>("/api/v1/browser/test-selector", { method: "POST", body: data }),
  close: (sessionId: string) =>
    request<any>("/api/v1/browser/close", { method: "POST", body: { session_id: sessionId } }),
};

// 7b. Browser Recorder
export const recorderApi = {
  start: (projectId: string, targetUrl: string) =>
    request<any>("/api/v1/recorder/start", { method: "POST", body: { project_id: projectId, target_url: targetUrl } }),
  status: (sessionId: string) =>
    request<any>(`/api/v1/recorder/status?session_id=${sessionId}`),
  recordAction: (sessionId: string, action: string, selector = "", value?: string) =>
    request<any>("/api/v1/recorder/action", { method: "POST", body: { session_id: sessionId, action, selector, value } }),
  stop: (sessionId: string) =>
    request<any>("/api/v1/recorder/stop", { method: "POST", body: { session_id: sessionId } }),
  inspect: (sessionId: string) =>
    request<{ session_id: string; elements_count: number; elements: any[] }>(`/api/v1/recorder/inspect/${sessionId}`),
  save: (data: { session_id: string; project_id: string; name: string; target_type: "test" | "flow"; description?: string }) =>
    request<any>("/api/v1/recorder/save", { method: "POST", body: data }),
};

// 8. Schedules
export const schedulesApi = {
  list: (projectId?: string) =>
    request<any[]>(`/api/v1/schedules${projectId ? `?project_id=${projectId}` : ""}`),
  create: (data: any) =>
    request<any>("/api/v1/schedules", { method: "POST", body: data }),
};

// 9. Reports & Analytics
export const reportsApi = {
  summary: (projectId?: string) =>
    request<any>(`/api/v1/reports/summary${projectId ? `?project_id=${projectId}` : ""}`),
  exportCsvUrl: (projectId?: string) =>
    `${API_BASE_URL}/api/v1/reports/export-csv${projectId ? `?project_id=${projectId}` : ""}`,
};

// 10. Administration & Audit
export const adminApi = {
  listUsers: () => request<any[]>("/api/v1/users"),
  listRoles: () => request<any[]>("/api/v1/roles"),
  listAuditLogs: (filters?: { limit?: number; action?: string; resource_type?: string }) => {
    const params = new URLSearchParams();
    if (filters?.limit) params.append("limit", String(filters.limit));
    if (filters?.action) params.append("action", filters.action);
    if (filters?.resource_type) params.append("resource_type", filters.resource_type);
    const qs = params.toString();
    return request<any[]>(`/api/v1/audit${qs ? `?${qs}` : ""}`);
  },
  exportAuditLogsUrl: (format: "csv" | "json" = "csv") =>
    `${API_BASE_URL}/api/v1/audit/export?format=${format}`,
  purgeRetention: (data?: { log_days?: number; screenshot_days?: number; dom_days?: number }) => {
    const params = new URLSearchParams();
    if (data?.log_days) params.append("log_days", String(data.log_days));
    if (data?.screenshot_days) params.append("screenshot_days", String(data.screenshot_days));
    if (data?.dom_days) params.append("dom_days", String(data.dom_days));
    const qs = params.toString();
    return request<any>(`/api/v1/audit/retention/purge${qs ? `?${qs}` : ""}`, { method: "POST" });
  },
};
