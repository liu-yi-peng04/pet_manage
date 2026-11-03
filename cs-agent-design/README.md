# cs-agent-design

**status: outdated**（历史线框 / 设计说明，不是当前实现的事实来源）

本目录是早期静态 HTML 设计稿（`cs-agent-design.html`，客服工单智能体方案，附带 `_shared/js/mermaid.min.js`）。前端构建、路由和 `frontend/src/api` 都不会引用这里。

## 和现行 Vue 实现的差距

设计稿描述的是另一条产品线：

- 路由：`/tickets`、`/tickets/:id`，以及客服工单队列。当前路由没有工单页。
- 角色：`admin` / `staff`（客服）/ `customer`。当前没有 `customer`；`staff` 是宠物店店员，入口是 `/workspace`，不是工单台。
- 接口：`/api/tickets` 与 `ticket_create` / `ticket_query` / `ticket_reply` / `ticket_resolve`。前端 API 模块里没有工单客户端。
- 页面范围停在「公共知识库问答 + 工单闭环」。现行宠智联是宠物店 / 医院 / 商城 / 寄养 / 选宠 / 训犬师。

`/chat` 仍在，但职责已是宠智联 AI 顾问，不是该稿里的企业客服问答。

## 建议

保持原位并以此 README 标明过时。不删文件，也不把 vendored mermaid 挪进 `docs/archive/`（搬迁噪声大、没有帮助实现）。实现以 `frontend/src` 与 `docs/最终说明.md` 为准。
