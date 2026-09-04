import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./embedded-mobile.css";

function enableEmbeddedMobileLayout() {
  const params = new URLSearchParams(window.location.search);
  const embeddedByPlatform = window.self !== window.top
    || params.has("backend_url")
    || document.referrer.includes("modelscope.cn");
  const mobileDevice = window.screen.width <= 700
    || /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
    || params.get("mobile_preview") === "1";

  // ModelScope 在手机上仍会给 iframe 分配 1280px 宽度，普通媒体查询无法识别窄屏。
  // 这里按真实设备宽度收窄应用画布，再由专用样式恢复移动端布局。
  if (embeddedByPlatform && mobileDevice) {
    const deviceWidth = Math.max(320, Math.min(window.screen.width, window.innerWidth, 430));
    document.documentElement.classList.add("embedded-mobile");
    document.documentElement.style.setProperty("--embedded-mobile-width", `${deviceWidth}px`);
  }
}

enableEmbeddedMobileLayout();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
