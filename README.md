# 宠智联（pet_manage）

连接养宠用户、宠物店、宠物医院、训犬师与运营者的多边 AI 服务平台。  
平台不自营库存；各端 AI 会话相互隔离。

## 文档（请读这一份）

👉 **[docs/最终说明.md](docs/最终说明.md)** — 架构、业务闭环、API、启动与演示账号  

索引：[docs/README.md](docs/README.md)

## 快速启动

默认是生产模式：缺少 `SECRET_KEY` / 正式 `DATABASE_URL` 时进程会拒绝启动，也不会写入演示口令。本地闭环请显式打开演示模式。

```bash
# 后端 :8000
cd backend
# Windows: copy .env.example .env
# Linux/macOS: cp .env.example .env && export APP_ENV=demo
# PowerShell: $env:APP_ENV="demo"
# cmd: set APP_ENV=demo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端 :5173
cd frontend
npm run dev
```

演示账号只在 `APP_ENV=demo`（或 `DEMO_MODE=true`）时由启动种子创建或重置。生产环境不会使用这些口令。

| 账号 | 密码 | 身份 |
|------|------|------|
| `demo_user` | `Passw0rd!a` | 养宠用户 |
| `storeA_mgr` / `storeA_staff` | `Passw0rd!a` | 店主 / 店员 |
| `hospital_mgr` | `Passw0rd!a` | 医院 |
| `trainer_demo` | `Passw0rd!a` | 训犬师 |
| `admin` | `admin123` | 超管（仅演示模式） |

技术栈：Vue3 + FastAPI + MySQL + Milvus + DeepSeek RAG。
