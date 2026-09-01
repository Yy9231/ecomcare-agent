import { Bot, CheckCircle2, Headphones, Package, Send, UserRound, XCircle } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { request, streamMessage } from "../lib/api";
import type { ChatMessage, Conversation, Reference } from "../types";
import CustomerHero from "./CustomerHero";
import ModelSelector from "./ModelSelector";

const prompts = [
  "订单 EC2026080001 的物流到哪了？",
  "我要为订单 EC2026080001 申请退货，商品不合适",
  "我的 Aurora X1 手机无法开机，应该怎么办？",
];

type ConversationSnapshot = {
  escalated: boolean;
  messages: ChatMessage[];
  latest_approval: { id: string; status: "pending" | "approved" | "rejected"; decided_at: string | null } | null;
};

type PendingApproval = {
  approvalId: string;
  placeholderId: string;
  knownMessageIds: string[];
};

function MessageBubble({ message }: { message: ChatMessage }) {
  const assistant = message.role === "assistant";
  const human = message.role === "human";
  const approvalCompleted = assistant && message.approvalStatus;
  return (
    <div className={`message-row ${message.role}`}>
      <div className="avatar">{assistant ? <Bot size={18} /> : human ? <Headphones size={18} /> : <UserRound size={18} />}</div>
      <div className="max-w-[82%]">
        {human ? <span className="human-agent-label">人工客服</span> : null}
        {approvalCompleted ? (
          <div className={`approval-result ${message.approvalStatus}`} role="status">
            <div className="approval-result-icon">
              {message.approvalStatus === "approved" ? <CheckCircle2 size={22} /> : <XCircle size={22} />}
            </div>
            <div>
              <span>{message.approvalStatus === "approved" ? "审批通过" : "审批未通过"}</span>
              <strong>{message.approvalStatus === "approved" ? "客服已同意退货申请" : "客服未同意退货申请"}</strong>
              <p>{message.content}</p>
            </div>
          </div>
        ) : (
          <div className="message-bubble">
            {message.content || <span className="typing">正在思考</span>}
          </div>
        )}
        {message.references?.length ? (
          <div className="mt-3 space-y-2">
            {message.references.map((reference) => (
              <div className="reference-card" key={reference.source}>
                <span>知识来源</span>
                <strong>{reference.title}</strong>
                <p>{reference.source} · v{reference.version}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function CustomerChat({ token, customerName, customerId }: {
  token: string;
  customerName: string;
  customerId: string;
}) {
  const [conversationId, setConversationId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", role: "assistant", content: "你好，我是 EcomCare。可以帮你查询订单、物流、商品说明和售后政策。" },
  ]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("正在连接服务…");
  const [busy, setBusy] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const seenHumanMessageIds = useRef(new Set<string>());

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      // 消息保存在 PostgreSQL；重新登录时优先恢复最近有内容的会话。
      try {
        const conversations = await request<Conversation[]>("/conversations", token);
        const conversation = conversations.find((item) => item.message_count > 0) ?? conversations[0] ?? await request<Conversation>("/conversations", token, { method: "POST", body: "{}" });
        const snapshot = await request<ConversationSnapshot>(`/conversations/${conversation.id}`, token);
        if (!cancelled) {
          setConversationId(conversation.id);
          snapshot.messages.filter((message) => message.role === "human").forEach((message) => seenHumanMessageIds.current.add(message.id));
          const restored = snapshot.messages.length ? snapshot.messages : [
            { id: "welcome", role: "assistant" as const, content: "你好，我是 EcomCare。可以帮你查询订单、物流、商品说明和售后政策。" },
          ];
          if (snapshot.latest_approval?.status === "pending") {
            const placeholderId = `approval-${snapshot.latest_approval.id}`;
            setMessages([...restored, { id: placeholderId, role: "assistant", content: "售后操作已暂停，等待客服审批。", pending: false }]);
            setPendingApproval({ approvalId: snapshot.latest_approval.id, placeholderId, knownMessageIds: snapshot.messages.map((message) => message.id) });
            setStatus("等待人工审批");
          } else {
            setMessages(restored);
            setStatus(snapshot.escalated ? "等待人工客服回复" : "Agent 在线");
          }
        }
      } catch (error) {
        if (!cancelled) setStatus(error instanceof Error ? error.message : "连接失败");
      }
    }
    void bootstrap();
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (!token || !conversationId) return;
    let cancelled = false;
    let timer: number | undefined;

    async function syncHumanReplies() {
      // 人工回复来自另一个浏览器请求，使用短轮询补齐当前 SSE 之外的新消息。
      try {
        const snapshot = await request<ConversationSnapshot>(`/conversations/${conversationId}`, token);
        const newReplies = snapshot.messages.filter((message) =>
          message.role === "human" && !seenHumanMessageIds.current.has(message.id),
        );
        const hasHumanReply = snapshot.messages.some((message) => message.role === "human");
        if (newReplies.length && !cancelled) {
          newReplies.forEach((message) => seenHumanMessageIds.current.add(message.id));
          setMessages((current) => [...current, ...newReplies]);
          setStatus("人工客服已回复");
        } else if (snapshot.escalated && !cancelled && !pendingApproval) {
          setStatus(hasHumanReply ? "人工客服在线" : "等待人工客服回复");
        }
      } catch {
        // 主发送流程负责展示错误；后台轮询静默重试，避免反复弹出短暂网络错误。
      }
      if (!cancelled) timer = window.setTimeout(() => void syncHumanReplies(), 1800);
    }

    void syncHumanReplies();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [conversationId, pendingApproval, token]);

  useEffect(() => {
    if (!pendingApproval || !token || !conversationId) return;
    const approval = pendingApproval;
    let cancelled = false;
    let timer: number | undefined;
    const knownMessageIds = new Set(approval.knownMessageIds);

    async function pollApprovalResult() {
      // 审批完成后用数据库中的最终 assistant 消息替换“等待审批”占位消息。
      try {
        const snapshot = await request<ConversationSnapshot>(`/conversations/${conversationId}`, token);
        const approvalResult = snapshot.latest_approval;
        const approvalStatus = approvalResult?.status;
        const finalMessage = snapshot.messages.find((message) =>
          message.role === "assistant" && !knownMessageIds.has(message.id),
        );
        if (finalMessage && approvalResult?.id === approval.approvalId && approvalStatus && approvalStatus !== "pending" && !cancelled) {
          setMessages((current) => current.map((message) => message.id === approval.placeholderId ? {
            ...message,
            content: finalMessage.content,
            pending: false,
            references: finalMessage.references,
            approvalStatus,
          } : message));
          setPendingApproval(null);
          setStatus(approvalStatus === "approved" ? "客服已同意退货申请" : "客服未同意退货申请");
          return;
        }
      } catch (error) {
        if (!cancelled) setStatus(error instanceof Error ? error.message : "审批结果同步失败");
      }
      if (!cancelled) timer = window.setTimeout(() => void pollApprovalResult(), 1500);
    }

    void pollApprovalResult();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [conversationId, pendingApproval, token]);

  const send = useCallback(async (content: string) => {
    if (!content.trim() || !token || !conversationId || busy || pendingApproval) return;
    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: userId, role: "user", content },
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);
    setInput("");
    setBusy(true);
    setStatus("Agent 正在分析意图…");
    let references: Reference[] = [];
    let requiresApproval = false;
    let approvalId = "";
    try {
      // 同一处理器消费工具、模型、审批和文本事件，驱动页面状态逐步变化。
      await streamMessage(token, conversationId, content, {
        onEvent(event, data) {
          if (event === "tool_started") setStatus(`正在调用 ${String(data.name)}…`);
          if (event === "tool_finished") {
            const result = data.result as { chunks?: Reference[] };
            references = result.chunks ?? [];
            setStatus("正在组织回答…");
          }
          if (event === "model_finished") setStatus(`${String(data.model)} 已生成回答`);
          if (event === "message_delta") {
            setMessages((current) => current.map((item) =>
              item.id === assistantId ? { ...item, content: item.content + String(data.content), references } : item,
            ));
          }
          if (event === "approval_required") {
            requiresApproval = true;
            approvalId = String(data.approval_id);
            setMessages((current) => current.map((item) => item.id === assistantId ? {
              ...item,
              pending: false,
              content: `售后操作已暂停，等待客服审批。审批编号：${String(data.approval_id)}`,
            } : item));
            setStatus("等待人工审批");
          }
          if (event === "error") throw new Error(String(data.message));
        },
      });
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, pending: false } : item));
      if (requiresApproval) {
        const snapshot = await request<ConversationSnapshot>(`/conversations/${conversationId}`, token);
        setPendingApproval({
          approvalId,
          placeholderId: assistantId,
          knownMessageIds: snapshot.messages.map((message) => message.id),
        });
        setStatus("等待人工审批");
      } else {
        setStatus("Agent 在线");
      }
    } catch (error) {
      setMessages((current) => current.map((item) => item.id === assistantId ? {
        ...item, pending: false, content: error instanceof Error ? error.message : "请求失败",
      } : item));
      setStatus("请求失败");
    } finally {
      setBusy(false);
    }
  }, [busy, conversationId, pendingApproval, token]);

  function submit(event: FormEvent) {
    event.preventDefault();
    void send(input);
  }

  return (
    <div className="customer-shell">
      <CustomerHero />
      <section className="chat-panel">
        <div className="chat-header">
          <div>
            <p className="font-semibold">与 EcomCare 对话</p>
            <p className="text-xs text-slate-500">当前客户：{customerName} · {customerId}</p>
          </div>
          <div className="chat-statuses"><ModelSelector token={token} /><span className="status-pill"><i />{status}</span></div>
        </div>
        <div className="messages">
          {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
          <div ref={endRef} />
        </div>
        <div className="prompt-row">
          {prompts.map((prompt) => <button key={prompt} disabled={busy || Boolean(pendingApproval)} onClick={() => void send(prompt)}>{prompt}</button>)}
        </div>
        <form className="composer" onSubmit={submit}>
          <Package size={18} className="text-slate-400" />
          <input name="customer-message" autoComplete="off" aria-label="咨询内容" disabled={Boolean(pendingApproval)} value={input} onChange={(event) => setInput(event.target.value)} placeholder={pendingApproval ? "等待客服处理当前售后申请…" : "输入订单号或描述你的问题…"} />
          <button disabled={busy || Boolean(pendingApproval) || !input.trim()} aria-label="发送"><Send size={17} /></button>
        </form>
        <p className="safe-note"><CheckCircle2 size={13} /> 高风险操作必须经人工审批，Agent 无法直接退款</p>
      </section>
    </div>
  );
}
