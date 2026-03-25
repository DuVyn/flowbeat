---
description: FlowBeat 项目后端核心规则。所有 AI 助手和开发者在 `backend/` 目录下生成、修改代码时，必须严格遵守此文件中的架构规范与代码限制。
applyTo: "backend/**/*"
---

# Backend 核心开发规则 (FastAPI + SQLAlchemy Async)

## 01. 架构分层与依赖隔离（严禁越界）
后端代码必须严格遵循四层架构，严禁跨层调用或逻辑混用：
- **Router 层 (`api/routers/`)**：仅负责接收 HTTP 请求、解析参数、调用 Service 层并返回标准响应。**严禁**在此层包含任何数据库操作或复杂业务逻辑。
- **Service 层 (`services/`)**：负责核心业务逻辑的处理。组合多个 Repository 完成事务操作。
- **Repository 层 (`repositories/`)**：仅负责与数据库的直接交互（CRUD）。必须使用 SQLAlchemy Async 语法。
- **Schema 层 (`schemas/`)**：所有的请求入参和响应出参必须使用 Pydantic 模型进行严格的数据校验。

## 02. 数据库与 ORM 规范 (SQLAlchemy Async)
1. **纯异步操作**：数据库操作必须 100% 异步。必须使用 `AsyncSession`，所有查询语句必须使用 `await db.execute(...)`。严禁混入同步的数据库调用代码。
2. **连接管理**：数据库 Session 必须通过 FastAPI 的 `Depends` (依赖注入) 获取，确保请求结束时自动释放连接。
3. **迁移管理**：所有的表结构变更（建表、加字段、改索引）**必须**通过生成 Alembic migration 脚本实现。严禁使用 `Base.metadata.create_all()` 直接修改线上或演示环境表结构。

## 03. API 接口与数据契约
1. **RESTful 规范**：路由命名必须为名词复数，统一使用 `/api/v1` 前缀。
2. **统一响应体**：所有 API（包含正常返回和异常捕获）的 JSON 返回结构必须严格一致：
   ```json
   {
     "code": 200,          // 业务状态码 (非 HTTP 状态码)
     "message": "success", // 提示信息
     "data": {}            // 实际载荷
   }
3. **入参校验**：对于字符串必须校验长度（min_length, max_length），对于数值必须校验范围（ge, le）。未通过 Pydantic 校验的请求必须由全局异常处理器拦截并返回统一格式。

## 04. 安全与鉴权
1. **JWT 机制**：鉴权必须使用 JWT，包含 Access Token 和 Refresh Token 逻辑。受保护的接口必须通过 Depends 进行权限拦截。
2. **密码存储**：严禁明文存储密码，必须使用单向哈希算法加密。
3. **敏感信息**：数据库连接串、JWT 密钥等必须从环境变量 .env 中读取。

## 05. 健壮性与可观测性
1. **全局异常拦截**：所有自定义业务异常必须交由 FastAPI 的全局异常处理器统一处理，转为标准响应体格式。
2. **结构化日志**：关键业务路径（如用户登录、写入操作）必须记录日志。错误日志必须包含：接口名、用户ID（若有）、错误摘要。