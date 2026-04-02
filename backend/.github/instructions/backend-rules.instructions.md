---
description: FlowBeat 项目后端核心规则。所有 AI 助手和开发者在任何目录下生成、修改代码或提供建议时，必须严格遵守此文件中的所有约束。
applyTo: "backend/**/*"
---

# FlowBeat 后端规则（BACKEND_RULES）

---

## 01. 目录结构建议

该部分仅为建议，非强制要求，但推荐遵循以下结构以保持项目整洁：

```
backend/
├─ app/
│  ├─ main.py                        # FastAPI 入口，注册路由与中间件
│  │
│  ├─ core/                          # 全局配置与通用能力（配置、安全、日志、异常）
│  ├─ db/                            # 数据库连接、会话、Base、迁移桥接
│  ├─ models/                        # SQLAlchemy ORM 模型（用户/歌曲/播放记录等）
│  ├─ schemas/                       # Pydantic 请求响应模型
│  ├─ repositories/                  # 数据访问层（面向表的 CRUD）
│  ├─ services/                      # 业务层（登录注册、推荐读取与降级、播放历史）
│  │
│  ├─ api/
│  │  └─ v1/                         # v1 接口（auth/music/playback/recommendations）
│  │
│  ├─ cache/                         # Redis 读写与 key 约定（rec:user:{id}:v1 等）
│  ├─ integrations/                  # 第三方集成（redis/minio 等客户端封装）
│  ├─ middleware/                    # 请求日志、鉴权上下文、CORS 等
│  └─ utils/                         # 工具函数（分页、时间格式、通用 helper）
│
├─ alembic/                          # 数据库迁移
├─ tests/                            # 后端测试（单元/集成/API）
├─ docs/                             # 后端接口文档与运行说明
└─ .venv/                            # backend 独立 Python 3.13 虚拟环境
```

---

## 02. 文件命名规范
- Python 文件使用小写字母和下划线（snake_case），例如 `main.py`、`user_repository.py`。
- 不同模块的文件应根据其功能进行命名，例如 `auth_service.py`、`user_schema.py`。
