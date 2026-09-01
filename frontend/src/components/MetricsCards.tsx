import { Activity, Bot, CheckCircle2, MessageSquareText } from "lucide-react";
import type { Metrics } from "../types";

export default function MetricsCards({ metrics }: { metrics: Metrics | null }) {
  const cards = [
    { label: "会话数", value: metrics?.conversations ?? 0, icon: MessageSquareText },
    { label: "自动解决率", value: `${Math.round((metrics?.resolution_rate ?? 0) * 100)}%`, icon: Bot },
    { label: "工具成功率", value: `${Math.round((metrics?.tool_success_rate ?? 0) * 100)}%`, icon: CheckCircle2 },
    { label: "平均工具耗时", value: `${metrics?.average_tool_latency_ms ?? 0} ms`, icon: Activity },
  ];
  return (
    <div className="metrics-grid">
      {cards.map(({ label, value, icon: Icon }) => (
        <article key={label} className="metric-card">
          <div className="metric-icon"><Icon size={18} /></div>
          <p>{label}</p><strong>{value}</strong>
        </article>
      ))}
    </div>
  );
}
