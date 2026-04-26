# FlowBeat

FlowBeat 是一个本科毕业设计项目，目标是实现可演示、可复现的在线音乐推荐系统。

## 项目定位

- 核心链路：数据处理 -> 推荐离线计算 -> 后端在线读取 -> 前端展示。
- 推荐策略分层：
  - 个性化主策略：Two-Tower。
  - 冷启动辅助策略：Content-based（基于注册偏好和内容画像）。
  - 兜底策略：全局非个性化（热门/最新等）。

## 当前实现状态

### 已上线能力

- 认证：注册、登录、登出、用户资料查询与更新。
- 音乐播放：歌曲详情接口、MinIO 预签名流地址接口。
- 搜索：顶栏关键词搜索（歌曲名/歌手/song_id），后端采用全文索引 + `has_more` 高性能分页。
- 推荐：全局热门推荐接口（含 Redis 缓存）。
- 用户行为：播放历史写入与分页查询。

### 推荐系统当前阶段

- `backend`：已提供全局热门推荐读取链路。
- `recsys`：已完成目录结构实体化（空目录 + 占位文件），尚未填充业务训练/推理实现。
- `content_based`：作为下一阶段优先打通的数据链路，计划见 docs 下独立文档。

## 技术栈

- 前端：Vue3 + TypeScript + pnpm
- 后端：FastAPI + SQLAlchemy Async
- 推荐：PyTorch
- 存储：MySQL + Redis + MinIO
- Python 包管理：uv（Python 3.13）

## 目录职责

- frontend：UI 渲染、交互、状态管理、API 调用。
- backend：在线 API、鉴权、业务逻辑、MySQL/Redis 读写、响应组装。
- recsys：特征工程、样本构建、训练、离线推理、评估、产物导出。
- scripts：工程脚本（清洗、导入、任务触发），不承载在线 API。
- data/raw：原始数据只读。

## 执行约定

- 仅在根目录维护一份 `README.md` 和一份 `.gitignore`。
- 大多数命令在子目录执行：`frontend`、`backend`、`recsys`、`scripts`。

## recsys 结构（已实体化）

当前 `recsys` 已创建并落盘以下结构，用于后续逐步填充实现：

```text
recsys/
├── configs/
│   ├── common/
│   ├── two_tower/
│   └── content_based/
├── features/
│   ├── shared/
│   ├── two_tower/
│   └── content_based/
├── datasets/
│   ├── two_tower/
│   └── content_based/
├── models/
│   └── two_tower/
├── training/
│   └── two_tower/
├── inference/
│   ├── two_tower/
│   ├── content_based/
│   ├── fusion/
│   └── writers/
├── evaluation/
│   ├── two_tower/
│   └── content_based/
├── artifacts/
├── checkpoints/
├── utils/
├── train.py
└── infer.py
```

说明：

- `two_tower` 与 `content_based` 已进行物理分层。
- 当前文件以中文占位说明为主，不包含业务骨架代码。

## 注册偏好存储（当前方案）

当前项目采用“用户-流派多对多关联”承载长期偏好，而不是一次性临时字段。

- ORM 关联表：`user_genre_preference_m2m`
- 设计目标：
  - 支撑冷启动召回。
  - 支撑长期偏好更新。
  - 支撑个性化链路降级时的稳定信号。

## 在线链路边界

- backend 请求链路仅读取推荐结果，不同步触发训练或重推。
- recsys 负责离线/准实时计算并写回存储（Redis 为主，MySQL 可选留档）。

## 开发入口（常用）

- 后端：在 `backend` 目录执行 `uv run` 相关命令。
- 前端：在 `frontend` 目录执行 `pnpm` 相关命令。
- 推荐：在 `recsys` 目录执行 `uv run` 相关命令。
