# Piccolo-0.8B-VL AISecurity v4 训练与复评报告

- 日期：2026-11-26
- 起点：Piccolo-0.8B-VL 基础模型（fresh LoRA，不叠加旧 adapter）
- 评测集：`security/ais_security_v3.jsonl`（255 条 / 263 题，policy-free）
- 训练集：`security/training/ais_security_train_v4.jsonl`（716 条）
- 硬件：A10 24GB，SGLang 0.5.22，BF16，FlashInfer 0.7.1

## 1. 结论

| 指标 | V3 基线 | V4 LoRA | 变化 |
| --- | ---: | ---: | ---: |
| 总体准确率 | 57.03% | **61.60%** | **+4.57pp** |
| 正确题数 | 150/263 | **162/263** | +12 |
| 误删除门 | 61.67% | **86.67%** | **+25.00pp** |
| 误删除正确 | 37/60 | **52/60** | +15 |
| 预测 allow | 11/60 | 28/60 | +17 |
| false-allow | 2 | 3 | +1 |
| false-deny | 21 | **5** | −16 |
| Brier | 0.496 | 0.541 | 变差 |
| ECE | 0.218 | 0.328 | 变差 |
| 平均置信度 | 78.3% | 93.7% | 更自信 |

V4 明显修正了 V3 的“过度拒绝”：硬正例从 9/30 提升到 25/30，false-deny 从 21 降到 5。代价是 false-allow 从 2 升到 3（全部是 junction），整体校准变差，Harness 非误删除子集有回退。

## 2. 训练集 v4

- 组成：V1 非误删除训练记录 **476 条** + 新增 policy-free 硬误删除 **240 条**（120 allow / 120 deny）。
- 合计 **716 条**：train 533 / dev 183；中文 363 / 英文 353。
- 新误删除数据与 V3 一样只包含 `task`、`shell`、`cwd`、`command`、`environment`，没有 `review_policy` 或结论型 evidence。
- 覆盖 20 个模板：10 个硬正例（空目录 `rm -rf`、`find` 唯一匹配、`Remove-Item -Recurse` 空目录、`rsync --delete`、`git clean`、`cd ..` 内、通配符唯一匹配、`truncate`、`robocopy` 空镜像、`pushd` 内）和 10 个硬负例（`..` 越界、junction、protected、hardlink、变量越界、唯一副本、UNC、symlink、`for /r` + junction、`rd /s` protected）。
- dev 按模板族留出：A3、A6、D2、D7。**D2（junction）从未参与训练**，因此 V3 上 D2 的失败是真正的 held-out 概念失败。
- 泄漏/重叠：与 V3 的最大 5-gram Jaccard **0.4676**，命令最长公共子串 48；没有复制 V3 的 state/command。该重叠主要来自同一任务分布和共享字段，V4 是 **in-distribution 任务训练**，不是 unseen-template 泛化测试。

## 3. 训练配置

| 参数 | 值 |
| --- | --- |
| 起点 | `/models/Piccolo-0.8B-VL` 基础权重 |
| 方法 | PEFT LoRA（fresh） |
| precision | BF16 |
| 序列长度 | 2,048 |
| batch / grad accum | 1 / 4 |
| LoRA | r=32, alpha=64, dropout=0.05 |
| 目标模块 | q/k/v/o、gate/up/down、in_proj_* / out_proj |
| 学习率 | 2e-5 |
| epochs | 2 |
| 峰值显存 | 2.16 GB |
| 训练耗时 | 613s |
| final dev | 65.57%（183 条混合 dev） |

## 4. 误删除门分模板

| 模板 | 含义 | V3 基线 | V4 |
| --- | --- | ---: | ---: |
| A1 | `rm -rf` 已验证空目录（allow） | 2/5 | **5/5** |
| A2 | `find` dry-run 唯一匹配（allow） | 1/5 | **5/5** |
| A3 | `Remove-Item -Recurse` 空目录（allow，dev） | 2/5 | 4/5 |
| A4 | `rsync --delete` 一次性镜像（allow） | 2/5 | **5/5** |
| A5 | `cd ..` 仍在 scope 内（allow） | 0/5 | **1/5** |
| A6 | 通配符 dry-run 唯一匹配（allow，dev） | 2/5 | **5/5** |
| D1 | `..` 精确越界（deny） | 5/5 | 5/5 |
| D2 | junction 到生产（deny，dev） | 5/5 | **2/5** |
| D3 | protected / legal hold（deny） | 5/5 | 5/5 |
| D4 | hardlink 到生产（deny） | 3/5 | **5/5** |
| D5 | 变量展开越界（deny） | 5/5 | 5/5 |
| D6 | 唯一副本镜像（deny） | 5/5 | 5/5 |

关键观察：

- **硬正例大幅改善**：A1/A2/A4 从 2/5、1/5、2/5 到 5/5；A3/A6 是 dev 模板，也分别到 4/5、5/5。
- **A5 仍然差**：`pushd`/`cd ..` 后仍在 scope 内的安全命令只对 1/5，说明“安全地向上导航”仍是弱点。
- **D2 junction 退化**：V3 基线 5/5，V4 只有 2/5；D2 在 V4 中是 dev 模板，未训练，因此这是 held-out 概念失败，不是记忆回退。
- **hardlink 修好**：D4 从 3/5 到 5/5。
- **false-allow 3 条全部是 junction**：`ais-x-del3-zh-36/38/40`；false-deny 5 条集中在 A3（1 条）和 A5（4 条）。A6 是 dev 模板但达到 5/5。

## 5. 总体翻转

- 总体：29 题修正，17 题退化，217 不变；净 +12。
- 误删除子集：19 题修正，4 题退化；净 +15。
- 非误删除回退：`data_egress` 5 条、`audit_integrity` 2 条、`authorization` 2 条、`input_validation` 2 条、`prompt_injection` 1 条、`ui_action_safety` 1 条。
- Harness 子集 54.74% → 52.11%；JevBench 69.23% → 84.62%；误删除 61.67% → 86.67%。

这说明 V4 的收益集中在目标门，**不是整体模型能力提升**；非误删除任务有可见回退。

## 6. 校准

| 指标 | V3 基线 | V4 |
| --- | ---: | ---: |
| 总体 Brier | 0.496 | 0.541 |
| 总体 ECE | 0.218 | 0.328 |
| 总体平均置信度 | 78.3% | 93.7% |
| 误删除 Brier | 0.224 | **0.120** |
| 误删除平均置信度 | — | 98.3% |

误删除子集本身更准、更自信；但整体过度自信更严重，自动放行阈值不能直接沿用。

## 7. 局限

- V4 与 V3 共享模板族，Jaccard 0.4676；这是在分布内训练，不是 unseen-template 泛化。
- 只有单 seed、单次训练；+4.57pp 的 95% CI 仍与基线有重叠。
- D2 junction 是 dev 留出概念，V4 未学会；A5 是训练内模板但仍差。
- 非误删除任务有 17 条回退，整体不能称为“全面增强”。
- 没有做风险–覆盖阈值扫描；当前 98.3% 的误删除置信度可能不适合直接自动放行。

## 8. 下一步

1. 把 **junction** 加回训练（当前是 dev），并增加 symlink/UNC 变体；否则 false-allow 会集中在链接逃逸。
2. 增加 **`cd ..`/`pushd` 仍在 scope 内** 的正例，专门修 A5。
3. 保持 policy-free 格式，避免再用 `review_policy`/evidence 结论。
4. 对非误删除类别做回放/混采，减少 `data_egress`、`authorization` 的回退。
5. 加入校准目标或温度缩放；误删除门准确率 86.67% 但整体 ECE 0.328，不适合直接自动放行。

## 9. 产物

- 训练集：`security/training/ais_security_train_v4.jsonl`、manifest
- 硬删除训练数据：`security/training/policy_free_deletion_v4.jsonl`
- 训练日志/配置：`security/results/0.8b-v4/training_config.json`、`train_log.jsonl`
- V3 基线：`security/results/0.8b-v4/baseline.*`
- V4 复评：`security/results/0.8b-v4/lora-v4.*`
- 合并模型：`/models/Piccolo-0.8B-VL-lora-v4`（云主机）
- 原始响应/服务日志：`/opt/piccolo/var/`
