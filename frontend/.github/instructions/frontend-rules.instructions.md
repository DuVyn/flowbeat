---
description: FlowBeat 项目前端核心规则。所有 AI 助手和开发者在任何目录下生成、修改代码或提供建议时，必须严格遵守此文件中的所有约束。
applyTo: "frontend/**/*"
---

# FlowBeat 前端规则（FRONTEND_RULES）

---

## 01. 目录结构建议

该部分仅为建议，非强制要求，但推荐遵循以下结构以保持项目整洁：

```
frontend/
├─ public/                     # 不经打包处理、原样输出的静态资源（如 favicon、robots）。
├─ src/
   ├─ assets/
   │  ├─ icons/                # 全站图标资源（建议优先 SVG）。
   │  ├─ images/               # 图片资源（logo、默认封面、占位图等）。
   │  └─ styles/               # 全局样式与设计变量（颜色、间距、字体、主题）。
   ├─ api/                     # 所有后端请求封装与接口分层。
   ├─ router/                  # 路由注册、路由表、导航守卫（登录态控制）。
   ├─ store/
   │  └─ modules/              # Pinia 状态分模块（auth/music/player/app）。
   ├─ layouts/                 # 页面骨架布局（主框架、认证页框架）。
   ├─ views/
   │  ├─ auth/                 # 登录/注册相关页面。
   │  ├─ home/                 # 首页/推荐页等聚合展示页面。
   │  ├─ category/             # 三大分类页面（发现、我的、历史等）。
   │  ├─ search/               # 搜索结果页与相关筛选展示页。
   │  └─ error/                # 错误页（404/500/无权限等）。
   ├─ components/
   │  ├─ common/               # 通用基础组件（按钮、输入框、卡片、空态）。
   │  ├─ navigation/           # 导航相关组件（侧栏、顶部栏、面包屑等）。
   │  ├─ music/                # 音乐业务组件（歌单网格、歌曲列表、行项）。
   │  └─ player/               # 底部播放器组件（信息区、控制区、进度/音量）。
   ├─ composables/             # 组合式逻辑复用（usePlayer/useAudio/useAuth 等）。
   ├─ utils/                   # 无状态工具函数与常量（时间格式化、存储封装等）。
   ├─ types/                   # 全局 TypeScript 类型声明（接口模型、DTO、状态类型）。
   ├─ directives/              # 自定义指令（如懒加载、权限显示）。
   └─ plugins/                 # Vue 插件注册入口（Pinia、i18n、埋点、UI库）。
```