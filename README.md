# FlowBeat

FlowBeat 是一个面向本科毕业设计的在线音乐推荐系统，覆盖从数据清洗、模型训练、接口服务到前端展示的完整链路。项目采用前后端分离架构，核心技术栈包括 Vue 3 + TypeScript、FastAPI + SQLAlchemy Async、PyTorch，以及 MySQL、Redis、MinIO 等基础设施。

## 项目目标

- 提供可运行、可演示的音乐推荐网站。
- 支持用户注册、登录、音乐播放、首页推荐、个性化推荐流和播放历史等核心能力。
- 支持离线推荐计算与在线结果读取的推荐系统架构。

## 当前实现状态

- 认证、播放、搜索、收藏、历史和全局热门推荐等主链路已经具备基础实现。
- `recsys/` 已完成目录骨架和 Two-Tower 训练入口，后续可继续补全训练、推理与评估流程。
- `content_based/` 方向作为冷启动和辅助推荐能力保留，便于后续接入注册偏好。

## 推荐分层

- 个性化主推荐：Two-Tower 模型。
- 冷启动辅助推荐：基于注册偏好和内容特征的 Content-based 推荐。
- 兜底推荐：全局热门、最新与规则榜单。

## 偏好设计

项目设计上预留了用户与流派的长期偏好关联，用于注册阶段和冷启动阶段的推荐补强。这样既能让新用户尽快得到可用推荐，也方便后续扩展更稳定的个性化策略。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router
- 后端：FastAPI、SQLAlchemy Async、Alembic、Redis、MinIO
- 推荐系统：PyTorch、Pandas、离线训练与推理脚本
- 基础设施：MySQL、Redis、MinIO、Docker Compose

## 仓库结构

- `frontend/`：Web 前端应用
- `backend/`：业务 API、鉴权、数据库读写、缓存与基础推荐接口
- `recsys/`：特征工程、训练、推理与模型产物
- `scripts/`：数据清洗、导入、上传和离线辅助脚本
- `data/raw/`：原始数据，只读
- `data/processed/`：清洗和加工后的数据
- `docs/`：项目文档、设计说明和论文材料

## 环境要求

- Node.js：`^20.19.0` 或 `>=22.12.0`
- Python：`3.13`
- 包管理：前端使用 `pnpm`，Python 项目使用 `uv`
- 数据库与服务：MySQL、Redis、MinIO

## 快速开始

### 1. 启动基础设施

先准备根目录 `.env`，可以参考 `.env.example`，然后启动基础服务：

```bash
docker compose up -d
```

### 2. 启动后端

进入 `backend/` 后，使用 `uv` 安装依赖并启动服务：

```bash
uv sync
uv run uvicorn app.main:app --reload
```

后端健康检查地址：`http://127.0.0.1:8000/health`

### 3. 启动前端

进入 `frontend/` 后安装依赖并启动开发服务器：

```bash
pnpm install
pnpm dev
```

### 4. 训练或推理推荐模型

进入 `recsys/` 后，使用 `uv` 执行训练或推理脚本。当前仓库中 Two-Tower 训练入口已可直接运行，常见命令示例：

```bash
uv run python train_two_tower.py
uv run python infer.py
```

### 5. 执行数据脚本

进入 `scripts/` 后运行数据清洗、导入或上传脚本。脚本目录中的路径通常以项目根目录为基准计算，避免依赖当前工作目录。

## 配置说明

根目录 `.env.example` 提供了常用环境变量模板，包括 MySQL、MinIO 和 Redis 的连接信息。启动后端前，请至少确认以下变量已正确配置：

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `AUTH_TOKEN_SECRET`

## 接口与健康检查

- 后端服务入口：`backend/app/main.py`
- 健康检查：`GET /health`
- 主要业务接口挂载在 `backend/app/api/` 下

## 常用入口

- 前端开发入口：`frontend/package.json`
- 后端启动入口：`backend/app/main.py`
- 推荐训练与推理入口：`recsys/train_two_tower.py`、`recsys/infer.py`
- 数据脚本入口：`scripts/global/` 与 `scripts/kkbox_cleanup/`

## 开发约定

- `data/raw/` 视为原始数据区，不直接修改
- Python 相关目录统一使用 `uv` 和 Python 3.13
- 前端依赖统一使用 `pnpm`
- 推荐结果遵循“离线计算 + 在线读取”的模式
