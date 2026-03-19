---
name: frontend
description: Flowbeat 前端开发规范
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# Flowbeat 前端开发规范

## 技术栈要求

- 核心框架：Vue 3 (强制使用 Composition API 和 `<script setup>` 语法)。
- 语言：TypeScript (开启严格模式，禁止使用 `any`，必须定义清晰的 Interface 或 Type)。
- 状态管理：Pinia。
- 网络请求：Axios (需统一封装请求拦截器和响应拦截器)。

## UI 风格与页面布局规范 (类 QQ 音乐风格)

在生成组件和页面样式时，必须遵循以下整体布局和视觉约束：

1. 整体架构：
   - 左侧：固定宽度的全局导航侧边栏 (Sidebar)。
   - 底部：固定高度的全局音频播放控制条 (Player Bar)，悬浮于所有内容之上。
   - 右侧/主体：自适应宽度的滚动内容区 (Main Content)，用于展示推荐歌单、排行榜、搜索结果等。
2. 视觉风格：
   - 采用现代化、扁平化的音乐流媒体 UI 风格。
   - 需考虑封面图的圆角 (通常为 8px 或 12px) 和悬浮态 (Hover) 时的阴影或播放按钮显现动画。
   - 列表项 (如歌曲列表) 需要清晰的斑马线或 Hover 高亮效果。
3. CSS 规范：样式代码需保持结构化，避免冗余的内联样式。

## 继承规则

必须严格遵守项目根目录的全局规范，代码与注释中严禁出现 Emoji。
