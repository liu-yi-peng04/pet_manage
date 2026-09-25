# 宠智联（pet_manage）

连接养宠用户、宠物店、宠物医院、训犬师与运营者的多边 AI 服务平台。  
平台不自营库存；各端 AI 会话相互隔离。

## 文档（请读这一份）

👉 **[docs/最终说明.md](docs/最终说明.md)** — 架构、业务闭环、API、启动与演示账号  

索引：[docs/README.md](docs/README.md)

## 快速启动

```bash
# 后端 :8000
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端 :5173
cd frontend
npm run dev
```

| 账号 | 密码 | 身份 |
|------|------|------|
| `demo_user` | `Passw0rd!a` | 养宠用户 |
| `storeA_mgr` / `storeA_staff` | `Passw0rd!a` | 店主 / 店员 |
| `hospital_mgr` | `Passw0rd!a` | 医院 |
| `trainer_demo` | `Passw0rd!a` | 训犬师 |
| `admin` | `admin123` | 超管 |

技术栈：Vue3 + FastAPI + MySQL + Milvus + DeepSeek RAG。
