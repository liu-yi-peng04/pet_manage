# pet-health-design

**status: outdated**（历史线框 / 设计说明，不是当前实现的事实来源）

本目录是早期静态 HTML 设计稿（`pet-health-design.html`，由 Trae 生成的报告页，青绿配色，并附带 `_shared/js/mermaid.min.js`）。前端构建不会引用这里的文件。

## 和现行 Vue 实现的差距

设计稿只规划了三条页面：

| 设计稿路由 | 设计稿内容 |
|------------|------------|
| `/chat` | 现有问答页加上 `pet_lookup` / `vaccine_schedule` |
| `/pets` | 宠物卡片 |
| `/pets/:id` | 档案 + 疫苗时间线 |

现行前端（`frontend/src/router/index.ts`）在此之外还有 `/home`、`/store`、`/orders`、`/booking`、`/workspace`、`/listings`、`/trainers`、`/operator`、`/dashboard`、`/kb` 等。角色是 `admin` / `user` / `staff` / `operator` / `trainer`，工作台按门店类型显隐 Tab，而不是这份稿里的「知识库 + 宠物档案」两页增量。

数据模型同样对不上：稿中新增的是 `Pet` / `VaccineRecord`；当前产品还有门店、商品订单、预约、寄养、待售宠物、训犬师等。

## 建议

保持原位，只加本说明。不迁入 `docs/archive/`，因为目录里有体积较大的 mermaid 脚本，搬动 diff 很大，且 `docs/README.md` 已指向本目录为早期线框。实现以 `frontend/` 与 `docs/最终说明.md` 为准。
