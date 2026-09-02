import { Headphones, LayoutDashboard, LockKeyhole, LogIn, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { login, saveSession, type AuthSession, type Role } from "../lib/auth";

export default function LoginPage({ role, onLogin }: { role: Role; onLogin: (session: AuthSession) => void }) {
  const agent = role === "agent";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const RoleIcon = agent ? LayoutDashboard : Headphones;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const session = await login(username.trim(), password);
      if (session.role !== role) throw new Error(agent ? "该账号没有客服工作台权限" : "该账号不是客户账号");
      saveSession(session);
      onLogin(session);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "登录失败，请重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="login-card" aria-labelledby="login-title">
        <div className={`login-role-icon ${role}`}><RoleIcon size={24} /></div>
        <p className="eyebrow">{agent ? "OPERATIONS ACCESS" : "CUSTOMER ACCESS"}</p>
        <h1 id="login-title">登录{agent ? "客服工作台" : "客户服务"}</h1>
        <p className="login-description">{agent ? "处理人工会话、风险审批并查看 Agent 轨迹" : "继续之前的订单咨询、售后申请与人工客服对话"}</p>
        <form className="login-form" onSubmit={(event) => void submit(event)}>
          <label htmlFor={`${role}-username`}>账号</label>
          <div className="login-input"><UserRound size={17} /><input id={`${role}-username`} name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></div>
          <label htmlFor={`${role}-password`}>密码</label>
          <div className="login-input"><LockKeyhole size={17} /><input id={`${role}-password`} name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></div>
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button className="login-button" disabled={busy || !username.trim() || password.length < 8}><LogIn size={17} />{busy ? "登录中…" : "登录"}</button>
        </form>
      </section>
    </div>
  );
}
