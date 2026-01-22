// Agent Types
export interface AgentProvider {
  name: string;
  url?: string;
}

export interface AgentCapabilities {
  streaming?: boolean;
  push_notifications?: boolean;
  state_transition_history?: boolean;
}

export interface AgentSkill {
  id: string;
  name: string;
  description: string;
  tags?: string[];
}

export interface AgentInterface {
  url: string;
  protocol_binding: string;
}

export interface AgentCard {
  name: string;
  description: string;
  version: string;
  protocol_versions?: string[];
  supported_interfaces?: AgentInterface[];
  provider?: AgentProvider;
  capabilities?: AgentCapabilities;
  skills?: AgentSkill[];
  default_input_modes?: string[];
  default_output_modes?: string[];
  icon_url?: string;
}

export interface RegisteredAgent {
  agent_id: string;
  card: AgentCard;
  registered_at: string;
  last_seen_at: string;
}

// App Types
export interface AppCard {
  name: string;
  description: string;
  scenario: string;
  mcp_endpoint: string;
  health_check_url: string;
  icon_url?: string;
  tags?: string[];
}

export interface RegisteredApp {
  app_id: string;
  card: AppCard;
  registered_at: string;
  last_seen_at: string;
  healthy: boolean;
}

// Task Types
export type TaskStateType =
  | "submitted"
  | "working"
  | "completed"
  | "failed"
  | "cancelled"
  | "input_required"
  | "rejected"
  | "auth_required";

export interface TaskStatus {
  state: TaskStateType;
  message?: string;
  timestamp: string;
}

export interface TextPart {
  type: "text";
  text: string;
}

export interface FilePart {
  type: "file";
  file: {
    name: string;
    mime_type: string;
    data?: string;
    uri?: string;
  };
}

export interface DataPart {
  type: "data";
  data: Record<string, unknown>;
}

export type Part = TextPart | FilePart | DataPart;

export type Role = "user" | "agent";

export interface Message {
  message_id: string;
  context_id?: string;
  task_id?: string;
  role: Role;
  parts: Part[];
  metadata?: Record<string, unknown>;
}

export interface Artifact {
  name?: string;
  description?: string;
  parts: Part[];
  index: number;
  append?: boolean;
  last_chunk?: boolean;
  metadata?: Record<string, unknown>;
}

export interface Task {
  id: string;
  context_id: string;
  status: TaskStatus;
  artifacts?: Artifact[];
  history?: Message[];
  metadata?: Record<string, unknown>;
}

// API Response Types
export interface AgentListResponse {
  agents: RegisteredAgent[];
  total: number;
}

export interface AppListResponse {
  apps: RegisteredApp[];
  total: number;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page_size: number;
  next_page_token: string;
}

// Tool Types (for Dynamic MCP)
export interface ToolInfo {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface AppToolsResponse {
  tools: ToolInfo[];
}
