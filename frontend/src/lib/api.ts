const API_URL = import.meta.env.VITE_API_URL
  ?? (import.meta.env.PROD ? "/api/v1" : "http://localhost:8000/api/v1");
const REQUEST_TIMEOUT_MS = 12_000;
const STREAM_IDLE_TIMEOUT_MS = 45_000;

type RequestOptions = RequestInit & {
  timeoutMs?: number;
  retries?: number;
};

class RequestTimeoutError extends Error {
  constructor() {
    super("连接服务超时，请重试");
    this.name = "RequestTimeoutError";
  }
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  options: RequestInit,
  timeoutMs: number,
) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const relayAbort = () => controller.abort(options.signal?.reason);
  options.signal?.addEventListener("abort", relayAbort, { once: true });
  try {
    return await fetch(input, { ...options, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted && !options.signal?.aborted) throw new RequestTimeoutError();
    throw error;
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener("abort", relayAbort);
  }
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, token?: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = REQUEST_TIMEOUT_MS, retries, ...fetchOptions } = options;
  const method = (fetchOptions.method ?? "GET").toUpperCase();
  const retryCount = retries ?? (method === "GET" ? 1 : 0);
  for (let attempt = 0; attempt <= retryCount; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${API_URL}${path}`, {
        ...fetchOptions,
        headers: {
          "Content-Type": "application/json",
          // 使用自定义头避免部署平台的代理层占用 Authorization。
          ...(token ? { "X-EcomCare-Token": token } : {}),
          ...fetchOptions.headers,
        },
      }, timeoutMs);
      if (response.ok) return response.json() as Promise<T>;
      if ([502, 503, 504].includes(response.status) && attempt < retryCount) continue;
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(body.detail ?? "请求失败", response.status);
    } catch (error) {
      if (error instanceof ApiError || attempt === retryCount) throw error;
      await new Promise((resolve) => window.setTimeout(resolve, 400));
    }
  }
  throw new Error("请求失败");
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
  const controller = new AbortController();
  let idleTimer = window.setTimeout(() => controller.abort(), STREAM_IDLE_TIMEOUT_MS);
  const resetIdleTimer = () => {
    window.clearTimeout(idleTimer);
    idleTimer = window.setTimeout(() => controller.abort(), STREAM_IDLE_TIMEOUT_MS);
  };
  let response: Response;
  try {
    response = await fetch(`${API_URL}/conversations/${conversationId}/messages/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-EcomCare-Token": token },
      body: JSON.stringify({ content }),
      signal: controller.signal,
    });
  } catch (error) {
    window.clearTimeout(idleTimer);
    if (controller.signal.aborted) throw new Error("Agent 响应超时，请重新发送");
    throw error;
  }
  if (!response.ok || !response.body) {
    window.clearTimeout(idleTimer);
    throw new Error("无法建立流式连接");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      resetIdleTimer();
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
  } catch (error) {
    if (controller.signal.aborted) throw new Error("Agent 响应超时，请重新发送");
    throw error;
  } finally {
    window.clearTimeout(idleTimer);
  }
}
