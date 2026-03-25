---
name: build-module
description: 在 flowbeat 后端项目中生成一个新的模块，严格遵守项目的技术栈和架构要求。
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# 生成后端模块（FlowBeat）

请在 backend 中实现一个完整 FastAPI 模块，遵守 router/service/repository/schema 分层。
要求：
- API 前缀 `/api/v1`
- 使用 SQLAlchemy Async
- 输入输出使用 Pydantic
- JWT 鉴权按现有项目方式接入
- 包含错误处理和基础日志

输出顺序：
1) 契约定义（URL/Method/请求/响应/错误码）
2) 文件清单
3) 完整代码
4) 迁移/初始化步骤
5) curl 或 httpie 测试命令

功能需求：
{{例如：获取当前用户推荐列表}}