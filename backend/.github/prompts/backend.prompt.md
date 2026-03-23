---
name: backend
description: Flowbeat 后端开发规范
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# Flowbeat 后端开发规范

## 技术栈要求

- 核心框架：FastAPI (利用其异步特性与 Pydantic 验证)。
- 数据库与 ORM：MySQL + SQLAlchemy (2.0+ 风格)。
- 数据库迁移：Alembic。
- 缓存与消息：Redis。
- 对象存储：MinIO (用于存储音频文件和封面图片)。
- 认证与授权：JWT (JSON Web Tokens)。
- 依赖管理：uv + pyproject.toml，安装依赖严格使用 uv add 命令。

## 架构与 API 规范预设

1. 目录分层：遵循 Router (路由) -> Service (业务逻辑) -> CRUD (数据访问) -> Model (数据模型) 的标准分层架构。
2. 统一响应格式：所有 API 返回的数据必须遵循以下标准 JSON 结构：
   {
   "code": 200,
   "message": "success",
   "data": {} // 实际载荷
   }
3. 异常处理：全局捕获异常并转化为上述统一响应格式，使用对应的 HTTP 状态码。
4. 类型提示：所有 Python 函数参数和返回值必须包含严格的 Type Hinting。

## 继承规则

必须严格遵守项目根目录的全局规范，代码与注释中严禁出现 Emoji。
