import type {
  RegisteredApp,
  AppCard,
  Task,
  TaskListResponse,
  AgentListResponse,
  AppListResponse,
  AppToolsResponse,
} from "../types";

const API_BASE = "";

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} - ${error}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// System API
export interface McpTool {
  name: string;
  description: string;
  category: string;
}

export interface SystemInfo {
  name: string;
  version: string;
  description: string;
  mcp: {
    endpoint: string;
    transport: string;
    tools: McpTool[];
  };
  health: {
    status: string;
    agents_count: number;
    apps_count: number;
    healthy_apps_count: number;
  };
  endpoints: {
    base_url: string;
    mcp_url: string;
    agent_card: string;
  };
}

export const systemApi = {
  getInfo: () => request<SystemInfo>("/system/info"),
};

// Agent API
export const agentApi = {
  list: () => request<AgentListResponse>("/agents"),

  delete: (agentId: string) =>
    request<void>(`/agents/${agentId}`, { method: "DELETE" }),
};

// App API
export const appApi = {
  list: (healthyOnly = false) =>
    request<AppListResponse>(`/apps${healthyOnly ? "?healthy_only=true" : ""}`),

  get: (appId: string) => request<RegisteredApp>(`/apps/${appId}`),

  create: (card: AppCard) =>
    request<RegisteredApp>("/apps", {
      method: "POST",
      body: JSON.stringify(card),
    }),

  update: (appId: string, card: AppCard) =>
    request<RegisteredApp>(`/apps/${appId}`, {
      method: "PUT",
      body: JSON.stringify(card),
    }),

  delete: (appId: string) =>
    request<void>(`/apps/${appId}`, { method: "DELETE" }),

  getTools: (appId: string) =>
    request<AppToolsResponse>(`/apps/${appId}/tools`),
};

// Task API
export const taskApi = {
  list: (params?: {
    context_id?: string;
    status?: string;
    page_size?: number;
    page_token?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.context_id) searchParams.set("context_id", params.context_id);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page_size)
      searchParams.set("page_size", String(params.page_size));
    if (params?.page_token) searchParams.set("page_token", params.page_token);

    const query = searchParams.toString();
    return request<TaskListResponse>(`/tasks${query ? `?${query}` : ""}`);
  },

  get: (taskId: string, historyLength?: number) => {
    const query = historyLength ? `?history_length=${historyLength}` : "";
    return request<Task>(`/tasks/${taskId}${query}`);
  },

  delete: (taskId: string) =>
    request<void>(`/tasks/${taskId}`, { method: "DELETE" }),
};
