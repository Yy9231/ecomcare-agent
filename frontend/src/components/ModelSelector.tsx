import { BrainCircuit, Check, KeyRound, LoaderCircle, Settings2, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { request } from "../lib/api";
import type { ModelOption, ModelPreferences } from "../types";

type Draft = { provider: string; model: string; baseUrl: string; apiKey: string };

function draftFrom(option: ModelOption): Draft {
  // API Key 永不回显；再次保存时留空表示沿用服务端已加密的旧值。
  return {
    provider: option.provider,
    model: option.model ?? "",
    baseUrl: option.base_url || option.default_base_url || "",
    apiKey: "",
  };
}

export default function ModelSelector({ token }: { token: string }) {
  const [preferences, setPreferences] = useState<ModelPreferences | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    void request<ModelPreferences>("/model/preferences", token)
      .then((result) => {
        if (!cancelled) {
          setPreferences(result);
          setDraft(draftFrom(result.selected));
        }
      })
      .catch((cause) => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : "模型配置加载失败");
      });
    return () => { cancelled = true; };
  }, [token]);

  function chooseProvider(provider: string) {
    const option = preferences?.options.find((item) => item.provider === provider);
    if (!option) return;
    setDraft(draftFrom(option));
    setError("");
    setOpen(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!draft || saving) return;
    setSaving(true);
    setError("");
    try {
      // 配置由当前登录账号的 JWT 绑定，前端不提交 account_id。
      const result = await request<ModelPreferences>("/model/preferences", token, {
        method: "PUT",
        // 云数据库冷连接可能超过普通读取时限，配置写入使用独立预算且不自动重试。
        timeoutMs: 30_000,
        body: JSON.stringify({
          provider: draft.provider,
          model: draft.provider === "deterministic" ? null : draft.model,
          base_url: draft.baseUrl,
          api_key: draft.apiKey,
        }),
      });
      setPreferences(result);
      setDraft(draftFrom(result.selected));
      setOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "保存模型配置失败");
    } finally {
      setSaving(false);
    }
  }

  const selected = preferences?.selected;
  const option = preferences?.options.find((item) => item.provider === draft?.provider);
  const publicDemo = preferences?.options.length === 1 && selected?.provider === "deterministic";
  return (
    <div className="model-selector-wrap">
      <label className="model-selector" title="选择仅对当前登录账号生效">
        {saving ? <LoaderCircle className="spinning" size={13} /> : <BrainCircuit size={13} />}
        <select aria-label="大模型供应商" disabled={saving || !preferences || publicDemo} value={open ? draft?.provider ?? "" : selected?.provider ?? ""} onChange={(event) => chooseProvider(event.target.value)}>
          {!preferences ? <option value="">检测模型…</option> : null}
          {preferences?.options.map((item) => <option key={item.provider} value={item.provider}>{item.label}{item.configured && item.model ? ` · ${item.model}` : item.provider === "deterministic" ? "" : "（待配置）"}</option>)}
        </select>
        {!publicDemo ? <button type="button" aria-label="配置当前模型" onClick={() => setOpen((value) => !value)}><Settings2 size={13} /></button> : null}
        <i>{selected?.provider === "deterministic" ? "RULE" : "AI"}</i>
      </label>
      {open && draft ? (
        <form className="model-config-popover" onSubmit={(event) => void save(event)}>
          <div className="model-config-title"><div><BrainCircuit size={16} /><strong>账号模型配置</strong></div><button type="button" aria-label="关闭模型配置" onClick={() => setOpen(false)}><X size={15} /></button></div>
          <p>仅当前账号使用。API Key 加密保存，保存后不会再次显示。</p>
          <label><span>供应商</span><select value={draft.provider} onChange={(event) => chooseProvider(event.target.value)}>{preferences?.options.map((item) => <option key={item.provider} value={item.provider}>{item.label}</option>)}</select></label>
          {draft.provider !== "deterministic" ? <>
            <label><span>Model</span><input required value={draft.model} onChange={(event) => setDraft({ ...draft, model: event.target.value })} placeholder="例如 deepseek-chat" /></label>
            <label><span>Base URL</span><input value={draft.baseUrl} onChange={(event) => setDraft({ ...draft, baseUrl: event.target.value })} placeholder={option?.default_base_url ?? "https://api.example.com/v1"} /></label>
            <label><span>API Key</span><div className="secret-input"><KeyRound size={13} /><input type="password" autoComplete="new-password" value={draft.apiKey} onChange={(event) => setDraft({ ...draft, apiKey: event.target.value })} placeholder={option?.has_api_key ? "已保存；留空则不修改" : option?.requires_api_key ? "请输入 API Key" : "可选"} /></div></label>
          </> : <div className="rule-mode-note">规则模式不调用外部模型，适合离线演示和故障降级。</div>}
          {error ? <div className="model-config-error" role="alert">{error}</div> : null}
          <div className="model-config-actions"><button type="button" onClick={() => setOpen(false)}>取消</button><button className="primary" disabled={saving}><Check size={13} />{saving ? "验证并保存…" : "保存并启用"}</button></div>
        </form>
      ) : null}
      {!open && error ? <span className="model-selector-error" role="status">{error}</span> : null}
    </div>
  );
}
