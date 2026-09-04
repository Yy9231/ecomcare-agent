import { Bot, Headphones, LayoutDashboard, LogOut } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { clearSession, loadSession, saveSession, validateSession, type AuthSession, type Role } from "./lib/auth";

const AgentWorkspace = lazy(() => import("./components/AgentWorkspace"));
const CustomerChat = lazy(() => import("./components/CustomerChat"));
const LoginPage = lazy(() => import("./components/LoginPage"));

type SystemRoute = Role;

function resolveSystemRoute(): SystemRoute {
  // 客户端和客服端使用独立 URL，避免在同一页面混用角色能力。
  // 线上使用 Hash 路由，刷新时 CDN 只需返回根页面，不依赖服务端 SPA fallback。
  const hashPath = window.location.hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  if (hashPath === "/agent" || hashPath.startsWith("/agent/")) return "agent";
  if (hashPath === "/customer" || hashPath.startsWith("/customer/")) return "customer";
  // ModelScope 会把应用放进 iframe 并移除 URL hash，使用 query 保留双角色入口。
  const queryRole = new URLSearchParams(window.location.search).get("role");
  if (queryRole === "agent" || queryRole === "customer") return queryRole;
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/") window.history.replaceState(null, "", "/#/customer");
  return path === "/agent" || path.startsWith("/agent/") ? "agent" : "customer";
}

export default function App() {
  const [route, setRoute] = useState<SystemRoute>(() => resolveSystemRoute());
  const isAgent = route === "agent";
  const SystemIcon = isAgent ? LayoutDashboard : Headphones;
  const [session, setSession] = useState<AuthSession | null>(() => loadSession(route));
  const [checking, setChecking] = useState(Boolean(session));
  const accessToken = session?.access_token;

  useEffect(() => {
    const handleHashChange = () => {
      const nextRoute = resolveSystemRoute();
      const nextSession = loadSession(nextRoute);
      setRoute(nextRoute);
      setSession(nextSession);
      setChecking(Boolean(nextSession));
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    document.title = isAgent ? "EcomCare 客服工作台" : "EcomCare 客户服务";
  }, [isAgent]);

  useEffect(() => {
    if (!accessToken) return;
    // 本地 Token 只用于恢复候选登录态，页面启动后仍由服务端 /auth/me 验证。
    let cancelled = false;
    validateSession(accessToken).then((renewed) => {
      if (!cancelled) {
        // /auth/me 会返回一个新签发的 Token。继续把它写回 state 会改变
        // accessToken，从而再次触发本 effect，造成页面永远停在“正在连接服务”。
        // 校验成功后保留本次已验证的 Token，只同步服务端返回的账号资料。
        const validated = { ...renewed, access_token: accessToken };
        saveSession(validated);
        setSession(validated);
        setChecking(false);
      }
    }).catch(() => {
      if (!cancelled) {
        clearSession(route);
        setSession(null);
        setChecking(false);
      }
    });
    return () => { cancelled = true; };
  }, [accessToken, route]);

  function logout() {
    clearSession(route);
    setSession(null);
  }

  return (
    <div className={`app-shell ${route} min-h-screen bg-[var(--canvas)] text-slate-900`}>
      <header className="topbar">
        <div className="brand-lockup">
          <div className="logo-mark"><Bot size={22} /></div>
          <div>
            <p className="font-display text-lg font-semibold leading-none">EcomCare</p>
            <p className="mt-1 text-[11px] tracking-[0.18em] text-slate-500">CUSTOMER INTELLIGENCE</p>
          </div>
        </div>
        <div className={`system-badge ${route}`}>
          <SystemIcon size={17} />
          <div>
            <strong>{isAgent ? "客服运营中心" : "客户服务中心"}</strong>
            <span>{isAgent ? "审批与审计" : "智能咨询与售后"}</span>
          </div>
        </div>
        {session ? <button className="logout-button" onClick={logout}><LogOut size={15} />退出登录</button> : null}
      </header>
      <main>
        <Suspense fallback={<div className="page-loading">正在进入{isAgent ? "客服工作台" : "客户服务"}…</div>}>
          {checking ? <div className="page-loading">正在恢复登录状态…</div> : session ? (
            isAgent ? <AgentWorkspace token={session.access_token} /> : <CustomerChat token={session.access_token} customerName={session.display_name} customerId={session.customer_id} />
          ) : <LoginPage role={route} onLogin={setSession} />}
        </Suspense>
      </main>
    </div>
  );
}
