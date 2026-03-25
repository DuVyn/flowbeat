---
name: build-page
description: 在 flowbeat 前端项目中生成一个新的页面，严格遵守项目的技术栈和风格要求。
agent: agent
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# 生成前端页面（FlowBeat）

请为 flowbeat 前端生成一个页面，严格遵守项目 rules：
- 技术：Vue3 + TS + script setup + Pinia + src/api 调用
- 风格：QQ 音乐风格借鉴（外观/布局）
- 输出顺序：
  1) 实现计划
  2) 修改文件清单
  3) 完整代码
  4) 本地验证步骤
  5) 风险与后续优化

页面需求：
{{在这里写需求，例如：推荐页，包含猜你喜欢、热门歌曲、最近播放}}