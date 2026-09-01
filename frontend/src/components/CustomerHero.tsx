import { Sparkles } from "lucide-react";

export default function CustomerHero() {
  return (
    <section className="hero-copy">
      <div className="eyebrow"><Sparkles size={14} /> Agent 驱动的售后体验</div>
      <h1>复杂问题，<br /><em>一次解决。</em></h1>
      <p>从知识检索到订单工具，再到风险操作的人工确认，每一步都有依据、可追踪。</p>
      <div className="capability-grid">
        <div><strong>6</strong><span>业务工具</span></div>
        <div><strong>100</strong><span>合成订单</span></div>
        <div><strong>HITL</strong><span>人工审批</span></div>
      </div>
    </section>
  );
}
