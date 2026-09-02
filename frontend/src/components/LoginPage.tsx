import { Headphones, LayoutDashboard, LockKeyhole, LogIn, UserPlus, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { login, registerCustomer, saveSession, type AuthSession, type Role } from "../lib/auth";

type CustomerMode = "login" | "register";

export default function LoginPage({ role, onLogin }: { role: Role; onLogin: (session: AuthSession) => void }) {
  const agent = role === "agent";
  const [mode, setMode] = useState<CustomerMode>("login");
  const registering = !agent && mode === "register";
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const RoleIcon = agent ? LayoutDashboard : Headphones;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (registering && password !== confirmPassword) throw new Error("两次输入的密码不一致");
      const session = registering
        ? await registerCustomer(username.trim(), displayName.trim(), password)
        : await login(username.trim(), password);
      if (session.role !== role) throw new Error(agent ? "该账号没有客服工作台权限" : "该账号不是客户账号");
      saveSession(session);
      onLogin(session);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "登录失败，请重试");
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode: CustomerMode) {
    setMode(nextMode);
    setError("");
    setPassword("");
    setConfirmPassword("");
  }

  const formReady = username.trim().length >= 3
    && password.length >= 8
    && (!registering || (displayName.trim().length >= 2 && confirmPassword === password));

  return (
    <div className="login-shell">
      <section className="login-card" aria-labelledby="login-title">
        <div className={`login-role-icon ${role}`}><RoleIcon size={24} /></div>
        <p className="eyebrow">{agent ? "OPERATIONS ACCESS" : "CUSTOMER ACCESS"}</p>
        <h1 id="login-title">{registering ? "注册客户账号" : `登录${agent ? "客服工作台" : "客户服务"}`}</h1>
        <p className="login-description">{agent ? "处理人工会话、风险审批并查看 Agent 轨迹" : registering ? "创建个人账号，聊天记录和售后进度会持续保存" : "继续之前的订单咨询、售后申请与人工客服对话"}</p>
        {!agent ? <div className="auth-mode-switch" aria-label="客户账号入口">
          <button type="button" className={mode === "login" ? "active" : ""} aria-pressed={mode === "login"} onClick={() => changeMode("login")}>登录</button>
          <button type="button" className={mode === "register" ? "active" : ""} aria-pressed={mode === "register"} onClick={() => changeMode("register")}>注册</button>
        </div> : null}
        <form className="login-form" onSubmit={(event) => void submit(event)}>
          {registering ? <>
            <label htmlFor="customer-display-name">昵称</label>
            <div className="login-input"><UserRound size={17} /><input id="customer-display-name" name="displayName" autoComplete="name" maxLength={40} value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="例如：小杨" /></div>
          </> : null}
          <label htmlFor={`${role}-username`}>账号</label>
          <div className="login-input"><UserRound size={17} /><input id={`${role}-username`} name="username" autoComplete="username" maxLength={32} value={username} onChange={(event) => setUsername(event.target.value)} placeholder={registering ? "3–32 位字母、数字或下划线" : "请输入账号"} /></div>
          <label htmlFor={`${role}-password`}>密码</label>
          <div className="login-input"><LockKeyhole size={17} /><input id={`${role}-password`} name="password" type="password" autoComplete={registering ? "new-password" : "current-password"} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={registering ? "至少 8 位" : "请输入密码"} /></div>
          {registering ? <>
            <label htmlFor="customer-confirm-password">确认密码</label>
            <div className="login-input"><LockKeyhole size={17} /><input id="customer-confirm-password" name="confirmPassword" type="password" autoComplete="new-password" maxLength={128} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="再次输入密码" /></div>
          </> : null}
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button className="login-button" disabled={busy || !formReady}>{registering ? <UserPlus size={17} /> : <LogIn size={17} />}{busy ? (registering ? "注册中…" : "登录中…") : (registering ? "注册并进入" : "登录")}</button>
        </form>
      </section>
    </div>
  );
}
