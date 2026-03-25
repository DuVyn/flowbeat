---
name: debug-bug
description: 为了排除和修复 bug，使用“导师模式”提供一个小白友好的排查流程。
---

<!-- Tip: Use /create-prompt in chat to generate content with agent assistance -->

# Bug 排查模式（小白友好）

我遇到一个 bug，请用“导师模式”帮我排查，要求：
- 先复述问题
- 给出最可能的 3 个原因（按概率排序）
- 每个原因给“如何验证”
- 给最小修复补丁
- 告诉我怎么避免再次发生

Bug 信息：
{{粘贴报错日志、截图、相关代码}}