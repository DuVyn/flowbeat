---
name: recsys
description: Flowbeat 推荐算法开发规范
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# Flowbeat 推荐算法开发规范

## 技术栈要求
- 核心框架：PyTorch (>=2.6.0), torchaudio (>=2.6.0), torchvision (>=0.21.0)。
- 语言：Python (要求遵循 PEP 8 规范，使用类型提示)。
- 依赖管理：uv + pyproject.toml，安装依赖严格使用 uv add 命令。

## 算法架构与数据流规范
1. 模型架构：主要基于双塔模型 (Two-Tower Model)，包含用户塔 (User Tower) 和物品塔 (Item/Track Tower)。模型定义需采用面向对象的 `nn.Module` 编写，结构清晰。
2. 数据交互模式：
   - 离线计算主导：算法端不直接处理来自前端的高并发实时请求。
   - 交互链路：从 MySQL/Redis 或消息队列读取用户行为日志和音频特征 -> 进行离线/近线批处理推理 -> 将生成的推荐候选集 (Item IDs) 或用户 Embedding 写入数据库或 Redis，供后端 FastAPI 直接读取。
3. 特征工程：编写特征处理脚本时，需保证模块化，方便后续集成 Pandas、Polars 或 PySpark 等数据处理库。

## 继承规则
必须严格遵守项目根目录的全局规范，代码与注释中严禁出现 Emoji。