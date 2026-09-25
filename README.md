# 宠智联

连接养宠用户、宠物店、宠物医院、训犬师与运营者的多边 AI 服务平台。  
平台不自营库存：商品与待售宠由商家上架履约；各端 AI 会话相互隔离。

## 文档

- **[整体架构说明（含架构图）](docs/architecture.md)** ← 当前权威架构文档  
- [文档目录](docs/README.md)

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | FastAPI + Tortoise ORM |
| 数据 | MySQL（业务 + 图片 Base64）/ Milvus（向量） |
| AI | DeepSeek + bge-m3 RAG + 工具调用 + SSE 流式 |

## 目录

```text
ai_agent/
├── backend/          # FastAPI
├── frontend/         # Vue3
├── docs/             # 架构文档
├── kb_docs_pet/      # 公共养宠语料
└── docker-compose.yml
```

## 本地启动

```bash
# 后端 :8000
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端 :5173
cd frontend
npm run dev
```

- 前端：http://localhost:5173/  
- 接口：http://127.0.0.1:8000/docs  

## 演示账号

| 账号 | 密码 | 身份 |
|------|------|------|
| `demo_user` | `Passw0rd!a` | 养宠用户 |
| `storeA_mgr` | `Passw0rd!a` | A 店店主 |
| `storeA_staff` | `Passw0rd!a` | A 店店员 |
| `hospital_mgr` | `Passw0rd!a` | 医院端 |
| `storeB_mgr` | `Passw0rd!a` | B 诊所端 |
| `trainer_demo` | `Passw0rd!a` | 训犬师 |
| `admin` | `admin123` | 超管 |

## 角色一览

| 端 | 能力摘要 |
|----|----------|
| 用户 | AI 顾问、选宠、商城、预约、宠物档案、订单 |
| 宠物店 | 待售宠、客户寄养、接收预约、商品订单、店内 AI |
| 医院 | 接收就诊预约（弹窗）、医院 AI（一人一账号） |
| 超管 | 公共知识库、运营台；**不上架商品** |

更多链路图、ER 图与 API 分组见 [docs/architecture.md](docs/architecture.md)。
