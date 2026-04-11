---
description: FlowBeat 项目个性化推荐算法端核心规则。所有 AI 助手和开发者在任何目录下生成、修改代码或提供建议时，必须严格遵守此文件中的所有约束。
applyTo: "recsys/**/*"
---

# FlowBeat 个性化推荐算法规则（RECOMMENDATION_RULES）

---

## 01. 目录结构建议

该部分仅为建议，非强制要求，但推荐遵循以下结构以保持项目整洁：

```
recsys/
├── configs/
│   ├── common/
│   ├── two_tower/
│   └── content_based/
├── features/
│   ├── shared/
│   ├── two_tower/
│   └── content_based/
├── datasets/
│   ├── two_tower/
│   └── content_based/
├── models/
│   └── two_tower/
├── training/
│   └── two_tower/
├── inference/
│   ├── two_tower/
│   ├── content_based/
│   ├── fusion/
│   └── writers/
├── evaluation/
│   ├── two_tower/
│   └── content_based/
├── artifacts/
├── checkpoints/
├── utils/
├── train.py
└── infer.py
```
