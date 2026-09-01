import { BrainCircuit, Check, ChevronRight, Clock3, MessageSquareReply, RefreshCw, Send, ShieldAlert, WandSparkles, Wrench, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { request } from "../lib/api";
import type { Approval, Conversation, Metrics, Trace } from "../types";
import MetricsCards from "./MetricsCards";
import ModelSelector from "./ModelSelector";

type Detail = {
  id: string;
  customer_id: string;
  escalated: boolean;
  messages: Array<{ id: string; role: string; content: string }>;
  traces: Trace[];
};

type RefreshState = "idle" | "loading" | "success";

const quickReplies = [
  "您好，我是人工客服，已经接手您的问题。",
  "我正在为您核实，请稍等片刻。",
  "已经为您登记处理，后续进度会及时同步。",
  "感谢您的耐心等待，如有其他问题可以继续留言。",
];

function ApprovalCard({ item, onDecision }: { item: Approval; onDecision: (id: string, decision: "approve" | "reject") => void }) {
  return (
    <article className="approval-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="pending-badge"><Clock3 size={12} /> 待审批</span>
          <h3>创建售后申请</h3>
          <p>{item.reason}</p>
        </div>
        <ShieldAlert className="text-amber-500" size={22} />
      </div>
      <div className="approval-meta"><span>客户 {item.customer_id}</span><span>订单 {item.order_id}</span></div>
      <div className="decision-row">
        <button className="reject" onClick={() => onDecision(item.id, "reject")}><X size={15} />拒绝</button>
        <button className="approve" onClick={() => onDecision(item.id, "approve")}><Check size={15} />批准并执行</button>
      </div>
    </article>
  );
}

function HumanReplyComposer({ conversationId, takingOver, replying, onReply, onSuggest }: {
  conversationId: string;
  takingOver?: boolean;
  replying: boolean;
  onReply: (conversationId: string, content: string) => Promise<boolean>;
  onSuggest: (conversationId: string) => Promise<string | null>;
}) {
  const [content, setContent] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  useEffect(() => setContent(""), [conversationId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim() || replying) return;
    if (await onReply(conversationId, content.trim())) setContent("");
  }

  async function suggest() {
    if (suggesting) return;
    setSuggesting(true);
    const suggestion = await onSuggest(conversationId);
    if (suggestion) setContent(suggestion);
    setSuggesting(false);
  }

  return (
    <form className="human-reply" onSubmit={(event) => void submit(event)}>
      <div className="human-reply-heading"><MessageSquareReply size={15} /><strong>人工客服回复</strong><button type="button" onClick={() => void suggest()} disabled={suggesting}><WandSparkles size={12} />{suggesting ? "生成中…" : "AI 回复建议"}</button><span>{takingOver ? "发送后自动接管会话" : "客户将实时收到消息"}</span></div>
      <div className="quick-replies" aria-label="客服常用语">
        {quickReplies.map((reply) => <button type="button" key={reply} onClick={() => setContent(reply)}>{reply}</button>)}
      </div>
      <div className="human-reply-composer">
        <textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="输入回复，或点击上方常用语…" maxLength={2000} />
        <button disabled={replying || !content.trim()} aria-label="发送人工回复"><Send size={15} />{replying ? "发送中" : "发送"}</button>
      </div>
    </form>
  );
}

function ConversationDetail({ detail, replying, onReply, onSuggest }: {
  detail: Detail | null;
  replying: boolean;
  onReply: (conversationId: string, content: string) => Promise<boolean>;
  onSuggest: (conversationId: string) => Promise<string | null>;
}) {
  if (!detail) return <div className="empty-detail">选择一条会话查看 Agent 执行轨迹</div>;
  return (
    <div className="detail-content">
      <div className="detail-title"><div><span>会话详情</span><strong>{detail.customer_id}</strong></div>{detail.escalated ? <b>已转人工</b> : <b className="resolved">自动处理中</b>}</div>
      <div className="detail-messages">
        {detail.messages.map((message) => <div key={message.id} className={`mini-message ${message.role}`}><span>{message.role === "user" ? "客户" : message.role === "human" ? "人工客服" : "Agent"}</span><p>{message.content}</p></div>)}
      </div>
      <HumanReplyComposer conversationId={detail.id} takingOver={!detail.escalated} replying={replying} onReply={onReply} onSuggest={onSuggest} />
      <div className="trace-list">
        <h4><Wrench size={15} /> Agent 执行轨迹</h4>
        {detail.traces.map((trace) => (
          <div key={trace.id} className={`trace-row ${trace.tool_name.startsWith("llm_") ? "model" : "tool"}`}>
            <i className={trace.success ? "success" : "failure"} />
            <div><strong>{trace.tool_name === "llm_generate" ? <><BrainCircuit size={11} /> 大模型生成</> : trace.tool_name}</strong><span>{trace.duration_ms} ms</span></div>
            <code>{JSON.stringify(trace.output).slice(0, 100)}</code>
          </div>
        ))}
        {!detail.traces.length ? <p className="text-sm text-slate-400">暂无工具调用</p> : null}
      </div>
    </div>
  );
}

export default function AgentWorkspace({ token }: { token: string }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [refreshState, setRefreshState] = useState<RefreshState>("idle");
  const [replying, setReplying] = useState(false);

  const loadDashboard = useCallback(async () => {
    // 三个互不依赖的接口并发加载，减少工作台首屏等待时间。
    const dashboardData = await Promise.all([
      request<Metrics>("/metrics/summary", token),
      request<Conversation[]>("/conversations", token),
      request<Approval[]>("/approvals", token),
    ]);
    const [metricData, conversationData, approvalData] = dashboardData;
    setMetrics(metricData);
    setConversations(conversationData);
    setApprovals(approvalData);
    setError("");
  }, [token]);

  useEffect(() => {
    if (refreshState !== "success") return;
    const timer = window.setTimeout(() => setRefreshState("idle"), 1600);
    return () => window.clearTimeout(timer);
  }, [refreshState]);

  useEffect(() => {
    void loadDashboard().catch((cause) => setError(cause instanceof Error ? cause.message : "加载失败"));
  }, [loadDashboard]);

  useEffect(() => {
    // 小规模演示采用轮询同步会话、未读和审批；生产环境可替换为推送通道。
    const timer = window.setInterval(() => void loadDashboard().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [loadDashboard]);

  async function refreshDashboard() {
    if (refreshState === "loading") return;
    setRefreshState("loading");
    setError("");
    try {
      await loadDashboard();
      setRefreshState("success");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "刷新失败，请稍后重试");
      setRefreshState("idle");
    }
  }

  async function selectConversation(id: string) {
    try {
      const conversation = await request<Detail>(`/conversations/${id}`, token);
      setDetail(conversation);
      // 已读位置由服务端持久化，刷新页面后未读数字不会恢复。
      await request(`/conversations/${id}/read`, token, { method: "POST", body: "{}" });
      setConversations((current) => current.map((item) => item.id === id ? { ...item, unread_count: 0 } : item));
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : "加载失败"); }
  }

  async function decide(id: string, decision: "approve" | "reject") {
    try {
      await request(`/approvals/${id}/decision`, token, {
        method: "POST",
        body: JSON.stringify({ decision, note: decision === "approve" ? "规则核验通过" : "人工审核拒绝" }),
      });
      await loadDashboard();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "审批失败"); }
  }

  async function sendHumanReply(conversationId: string, content: string) {
    if (replying) return false;
    setReplying(true);
    try {
      const message = await request<Detail["messages"][number] & { conversation_escalated: boolean }>(`/conversations/${conversationId}/human-replies`, token, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setDetail((current) => current?.id === conversationId ? { ...current, escalated: message.conversation_escalated, messages: [...current.messages, message] } : current);
      setConversations((current) => current.map((item) => item.id === conversationId ? { ...item, escalated: true } : item));
      setError("");
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "人工回复发送失败");
      return false;
    } finally {
      setReplying(false);
    }
  }

  async function createSuggestion(conversationId: string) {
    try {
      const result = await request<{ content: string }>(`/model/reply-suggestions/${conversationId}`, token, { method: "POST", body: "{}" });
      setError("");
      return result.content;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "回复建议生成失败");
      return null;
    }
  }

  const pending = approvals.filter((item) => item.status === "pending");
  return (
    <div className="workspace-shell">
      <div className="workspace-heading">
        <div><p className="eyebrow">OPERATIONS CONSOLE</p><h1>客服工作台</h1><span>观察 Agent、处理风险操作、追踪真实效果</span></div>
        <div className="workspace-actions">
          <ModelSelector token={token} />
          <button
            className={`refresh-button ${refreshState}`}
            onClick={() => void refreshDashboard()}
            disabled={refreshState === "loading"}
            aria-busy={refreshState === "loading"}
            aria-live="polite"
          >
            <RefreshCw className={refreshState === "loading" ? "refresh-icon spinning" : "refresh-icon"} size={15} />
            {refreshState === "loading" ? "刷新中…" : refreshState === "success" ? "已更新" : "刷新数据"}
          </button>
        </div>
      </div>
      {error ? <div className="error-banner">{error}</div> : null}
      <MetricsCards metrics={metrics} />
      <div className="workspace-grid">
        <section className="panel conversations-panel">
          <div className="panel-heading"><div><span>最近会话</span><strong>{conversations.length}</strong></div><p>实时审计 Agent 行为</p></div>
          <div className="conversation-list">
            {conversations.map((item) => (
              <button
                key={item.id}
                className={detail?.id === item.id ? "selected" : undefined}
                aria-pressed={detail?.id === item.id}
                onClick={() => void selectConversation(item.id)}
              >
                <div className="customer-token">
                  {item.customer_name.slice(0, 1)}
                  {item.unread_count ? <span className="unread-badge" aria-label={`${item.unread_count} 条未读客户消息`}>{item.unread_count > 99 ? "99+" : item.unread_count}</span> : null}
                </div>
                <div><strong>{item.customer_name}</strong><span>{item.customer_id} · {new Date(item.latest_activity_at).toLocaleString("zh-CN")}</span></div>
                {item.escalated ? <em>人工</em> : <em className="auto">Agent</em>}
                <ChevronRight size={16} />
              </button>
            ))}
            {!conversations.length ? <p className="empty-list">等待第一条客户会话</p> : null}
          </div>
        </section>
        <section className="panel detail-panel"><ConversationDetail detail={detail} replying={replying} onReply={sendHumanReply} onSuggest={createSuggestion} /></section>
        <section className="panel approvals-panel">
          <div className="panel-heading"><div><span>风险操作审批</span><strong>{pending.length}</strong></div><p>Human-in-the-loop</p></div>
          <div className="approval-list">
            {pending.map((item) => <ApprovalCard key={item.id} item={item} onDecision={decide} />)}
            {!pending.length ? <div className="approval-empty"><CheckCircleMark /><strong>当前无待审批操作</strong><span>Agent 的写操作会在这里暂停</span></div> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

function CheckCircleMark() {
  return <div className="check-mark"><Check size={22} /></div>;
}
