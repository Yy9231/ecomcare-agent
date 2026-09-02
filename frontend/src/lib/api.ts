const API_URL = import.meta.env.VITE_API_URL
  ?? (import.meta.env.PROD ? "/api/v1" : "http://localhost:8000/api/v1");

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, token?: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(body.detail ?? "请求失败", response.status);
  }
  return response.json() as Promise<T>;
}

type StreamHandlers = {
  onEvent: (event: string, data: Record<string, unknown>) => void;
};

export async function streamMessage(
  token: string,
  conversationId: string,
  content: string,
  handlers: StreamHandlers,
) {
  // fetch + ReadableStream 支持 POST 请求体；原生 EventSource 只能发起 GET。
  const response = await fetch(`${API_URL}/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ content }),
  });
  if (!response.ok || !response.body) throw new Error("无法建立流式连接");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    // SSE 块可能被拆在两个网络包中，最后一个不完整块必须留到下一轮拼接。
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const lines = block.split("\n");
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
      const dataLines = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim());
      if (event && dataLines.length) handlers.onEvent(event, JSON.parse(dataLines.join("\n")));
    }
    if (done) break;
  }
}
