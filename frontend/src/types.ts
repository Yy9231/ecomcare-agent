export type Reference = { title: string; source: string; content: string; version: string };

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "human";
  content: string;
  references?: Reference[];
  pending?: boolean;
  approvalStatus?: "approved" | "rejected";
};

export type Conversation = {
  id: string;
  customer_id: string;
  customer_name: string;
  status: string;
  escalated: boolean;
  created_at: string;
  latest_activity_at: string;
  message_count: number;
  unread_count: number;
};

export type Approval = {
  id: string;
  conversation_id: string;
  customer_id: string;
  order_id: string;
  action: string;
  reason: string;
  status: string;
  created_at: string;
};

export type Trace = {
  id: string;
  tool_name: string;
  success: boolean;
  duration_ms: number;
  output: Record<string, unknown>;
};

export type Metrics = {
  conversations: number;
  resolution_rate: number;
  escalation_rate: number;
  tool_success_rate: number;
  average_tool_latency_ms: number;
};

export type ModelOption = {
  provider: string;
  label: string;
  model: string | null;
  base_url: string;
  default_base_url: string | null;
  requires_api_key: boolean;
  configured: boolean;
  has_api_key: boolean;
  source: "account" | "server" | "rule" | "none";
};

export type ModelPreferences = {
  selected: ModelOption;
  options: ModelOption[];
};
