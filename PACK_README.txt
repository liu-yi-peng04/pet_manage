# 宠智联 / ai_agent 完整包（含已安装依赖）

打包时间：见压缩包文件名日期。

## 包含内容
- 完整源码（backend / frontend / docs 等）
- Python 虚拟环境：backend/.venv（已 pip install）
- 前端依赖：frontend/node_modules（已 npm install）
- 精确版本：backend/requirements-lock.txt、frontend/package-lock.json

## 解压后启动（本机路径尽量与原路径接近；若换盘符见下方说明）

### 后端
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

### 前端
cd frontend
npm run dev

## 若换机器后 .venv 无法启动（脚本里写死了原 Python 路径）
cd backend
python -m venv .venv_new
.\.venv_new\Scripts\python.exe -m pip install -r requirements-lock.txt
# 然后把 .venv_new 当作新环境使用，或删除旧 .venv 后改名为 .venv

## 仅重装前端依赖
cd frontend
npm ci

## 注意
- 数据库连接与密钥在 backend/.env（若未随包提供需自行配置）
- sentence-transformers / torch 体积大，已装在 .venv 中，无需再下载模型权重以外的包（首次跑 embedding 仍可能拉模型）
