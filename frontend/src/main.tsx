import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Font Awesome toàn giao diện (Đợt nâng cấp 2 mục 2) — bản npm, không phụ thuộc CDN.
import "@fortawesome/fontawesome-free/css/all.min.css";
// Font chữ tiếng Việt Be Vietnam Pro (mục 8/11) — nạp các trọng số dùng trong UI.
import "@fontsource/be-vietnam-pro/400.css";
import "@fontsource/be-vietnam-pro/500.css";
import "@fontsource/be-vietnam-pro/600.css";
import "@fontsource/be-vietnam-pro/700.css";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
