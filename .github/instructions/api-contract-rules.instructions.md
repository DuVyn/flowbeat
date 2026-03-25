---
description: FlowBeat 项目 API 契约规则。所有 AI 助手在涉及前后端数据交互、新增或修改接口时，必须严格遵守契约优先原则。
applyTo: "**/*"
---

# API 契约核心规则 (API Contract Rules)

## 01. 契约优先原则 (Contract First)
严禁在未定义接口契约的情况下直接编写后端路由逻辑或前端请求代码。新增或修改接口前，必须先以标准结构输出接口定义，包含以下必填字段：
- **URL**：接口绝对路径（需符合 `/api/v1/...` 前缀规范）。
- **Method**：HTTP 请求方法（GET, POST, PUT, DELETE）。
- **请求参数**：清晰划分 Path, Query, Body 参数，明确数据类型及是否必填。
- **响应示例**：必须提供符合项目标准结构（code, message, data）的 JSON 格式示例。
- **错误码**：列出该接口可能触发的业务错误码及具体场景。

## 02. 核心接口优先开发 (MVP Interfaces)
在以下核心接口完全跑通之前，避免推荐或生成非必要的扩展接口代码（用户明确要求除外）：
1. `POST /api/v1/auth/register` (用户注册)
2. `POST /api/v1/auth/login` (用户登录/获取令牌)
3. `GET /api/v1/songs/{id}` (获取歌曲详情与播放资源)
4. `GET /api/v1/recommendations` (获取个性化推荐流)
5. `GET /api/v1/recommendations/cold-start` (获取冷启动推荐流)

## 03. 文档强制同步 (Change Management)
任何对现有 API 接口的变更（包含增删参数、修改类型、调整路径或改变业务逻辑），必须同时提供对 `docs/` 目录下相关 API 文档的修改代码或更新指导。严禁制造代码与文档不一致的状况。