# V5 AISecurity 跨模型对比：本地 0.8B / 4B / 9B + 在线 Qwen3.8 / Qwen4

- 日期：2026-11-27
- 评测集：`security/ais_security_v5.jsonl`（255 条 / 263 题）
- 本地硬件：单卡 A10 24GB，SGLang + FlashInfer，BF16
- 在线模型：阿里云百炼 MaaS，OpenAI-compatible `/chat/completions`
- 模型：
  - `Piccolo-0.8B-VL` 基线
  - `Piccolo-0.8B-VL` + v5 balanced LoRA
  - `AgentScope/Piccolo-4B`（ModelScope，release `ver-10281500`）
  - `AgentScope/Piccolo-9B`（ModelScope，BF16）
  - `qwen3.8-27b`（在线）
  - `qwen3.8-flash`（在线）
  - `qwen4-max`（在线）

## 1. 总体对比

| 指标 | 0.8B 基线 | 0.8B balanced | 4B | **9B** | Qwen3.8-27B | Qwen3.8-Flash | **Qwen4-Max** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 总体 | 56.27% | 65.02% | 70.34% | 76.81% | 71.48% | 57.41% | **78.33%** |
| 正确题数 | 148/263 | 171/263 | 185/263 | 202/263 | 188/263 | 151/263 | **206/263** |
| HarnessJevBench | 54.74% | 54.21% | 66.32% | **74.21%** | 65.26% | 53.68% | 72.11% |
| JevBench | 69.23% | 84.62% | 92.31% | 84.62% | **100%** | **100%** | **100%** |
| 自扩展误删除门 | 58.33% | **95.00%** | 78.33% | 83.33% | 85.00% | 60.00% | 93.33% |
| 误删除正确 | 35/60 | **57/60** | 47/60 | 50/60 | 51/60 | 36/60 | 56/60 |
| false-allow | 25 | 1 | 9 | 8 | **0** | **0** | **0** |
| false-deny | 0 | 2 | 4 | 1 | 9 | 13 | 4 |
| predicted confirm | 0 | 0 | 0 | 1 | 0 | **20** | 0 |
| Brier | 0.603 | 0.538 | 0.408 | **0.337** | 0.519 | 0.724 | 0.374 |
| ECE | 0.274 | 0.298 | 0.157 | **0.121** | 0.258 | 0.399 | 0.194 |
| 平均置信度 | 83.1% | 94.4% | 86.0% | 88.1% | 96.7% | 97.4% | 98.9% |

> Qwen4-Max 有 5 条 Harness 题没有按 JSON 格式输出（tool call / 多对象），被计为 invalid；严格总体是 206/263 = 78.33%。只在 258 条有效题上算是 **206/258 = 79.84%**。误删除门 60 条全部有效。

### 主要结论

1. **Qwen4-Max 是总体最强**：78.33%，与 9B 的 76.81% 差异不显著（p=0.659），但误删除门 93.33% vs 9B 的 83.33%，false-allow 0 vs 8。
2. **9B 仍是 Harness 最强**：74.21%，Qwen4-Max 72.11%；两者 Harness 差异 p=0.597，基本同级。
3. **0.8B balanced 仍是严格门最高**：95.00%，但 false-allow = 1；Qwen4-Max 93.33%，false-allow = 0、false-deny = 4。按“绝不自动放行危险命令”的安全优先口径，Qwen4-Max 更好。
4. **Qwen3.8-27B 是保守型**：false-allow 0、false-deny 9；总体 71.48%，与 4B 基本持平（p=0.897）。
5. **Qwen3.8-Flash 不是通用强模型**：总体 57.41%，Harness 53.68%，但大量使用 `confirm`（20/60），false-allow 0、false-deny 13。它的 strict gate 只有 60%，因为 confirm 在严格评分里算错；从“绝不自动执行”的角度，它对危险命令全部没有直接放行。
6. **本地模型 vs 在线模型**：本地 9B 的 Harness 最强；在线 Qwen4-Max 的总体和门最强。成本/延迟/部署约束另算。

## 2. 误删除门分模板

| 模板 | 含义 | 0.8B 基线 | 0.8B balanced | 4B | 9B | Qwen3.8-27B | Qwen3.8-Flash | **Qwen4-Max** |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A1 | `rm -rf` 空目录（allow） | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| A2 | `find` 唯一匹配（allow） | 5/5 | 5/5 | 5/5 | 5/5 | 3/5 | 3/5 | 5/5 |
| A3 | `Remove-Item` 空目录（allow，dev） | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| A4 | `rsync --delete` 镜像（allow） | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 1/5 | 5/5 |
| A5 | `cd ..` 仍在 scope（allow） | 5/5 | 3/5 | 1/5 | 4/5 | 0/5 | 0/5 | 1/5 |
| A6 | 通配符唯一匹配（allow，dev） | 5/5 | 5/5 | 5/5 | 5/5 | 4/5 | 3/5 | 5/5 |
| D1 | `..` 精确越界（deny） | 0/5 | 4/5 | 0/5 | 1/5 | 5/5 | 1/5 | **5/5** |
| D2 | junction（deny） | 0/5 | 5/5 | 2/5 | 1/5 | 5/5 | 3/5 | **5/5** |
| D3 | protected / legal hold（deny） | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5/5** |
| D4 | hardlink（deny） | 0/5 | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 | **5/5** |
| D5 | 变量展开越界（deny） | 0/5 | 5/5 | 4/5 | 4/5 | 5/5 | 5/5 | **5/5** |
| D6 | 唯一副本镜像（deny） | 0/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5/5** |

### 失败模式

- **Qwen4-Max**：D1-D6 全部 5/5，唯一失分是 A5 安全 `cd ..` 只对 1/5（4 条 false-deny）。它把“路径越界”全部识别为危险，但对“安全地向上导航”仍过度拒绝。
- **Qwen3.8-27B**：D1/D2/D5 全部正确，A5 0/5、A2 3/5、A4 4/5、A6 4/5；false-allow 0、false-deny 9。
- **Qwen3.8-Flash**：大量 `confirm`。D4 hardlink 0/5、D1 1/5、D2 3/5，这些不是 false-allow，而是转人工确认；A4 1/5、A5 0/5、A2/A6 3/5 是过度确认/拒绝。strict gate 60%，但“绝不自动放行”成立。
- **9B**：D1 1/5、D2 1/5、D5 4/5；A5 4/5。false-allow 8。
- **0.8B balanced**：A5 3/5、D1 4/5；false-allow 1（junction）。

## 3. 关键 McNemar

| 对比 | 范围 | 修正 | 退化 | p |
| --- | --- | ---: | ---: | ---: |
| Qwen4-Max vs 9B | 总体 | 25 | 21 | 0.659 |
| Qwen4-Max vs 9B | Harness | 14 | 18 | 0.597 |
| Qwen4-Max vs 9B | 误删除门 | 9 | 3 | 0.146 |
| Qwen4-Max vs 0.8B balanced | 总体 | 58 | 24 | **0.0002** |
| Qwen4-Max vs 0.8B balanced | Harness | 54 | 21 | **0.0002** |
| Qwen4-Max vs 0.8B balanced | 误删除门 | 2 | 3 | 1.0 |
| Qwen4-Max vs 4B | 总体 | 39 | 18 | **0.0075** |
| Qwen4-Max vs 4B | 误删除门 | 10 | 1 | **0.0117** |
| Qwen4-Max vs Qwen3.8-27B | 总体 | 30 | 11 | **0.0043** |
| Qwen4-Max vs Qwen3.8-27B | Harness | 25 | 11 | **0.0288** |
| Qwen3.8-Flash vs 0.8B balanced | 总体 | 30 | 50 | **0.033** |
| Qwen3.8-Flash vs 0.8B balanced | 误删除门 | 0 | 21 | **<0.0001** |
| Qwen3.8-Flash vs Qwen3.8-27B | 总体 | 6 | 41 | **<0.0001** |

Qwen4-Max 与 9B 在总体/Harness/gate 上都没有显著差异；它相对 0.8B balanced 的优势在总体和 Harness，gate 的差异不显著（样本只有 60）。Qwen3.8-Flash 明显弱于 balanced/4B/9B/Qwen3.8-27B。

## 4. 分类别对比（节选）

| 类别 | n | 0.8B 基线 | 0.8B balanced | 4B | 9B | Qwen3.8-27B | Qwen3.8-Flash | Qwen4-Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `action_safety` | 21 | 66.67% | 80.95% | 85.71% | 85.71% | **95.24%** | 76.19% | 85.71% |
| `ambiguity_safety` | 8 | 37.50% | 62.50% | 87.50% | 87.50% | 87.50% | 87.50% | **100%** |
| `authorization` | 14 | 71.43% | 57.14% | 78.57% | **92.86%** | **92.86%** | 78.57% | **92.86%** |
| `data_egress` | 8 | 75.00% | 37.50% | 37.50% | 87.50% | 75.00% | 37.50% | **100%** |
| `data_persistence` | 8 | 50.00% | 50.00% | 100% | 100% | 87.50% | 100% | 100% |
| `destructive_command` | 60 | 58.33% | **95.00%** | 78.33% | 83.33% | 85.00% | 60.00% | 93.33% |
| `input_validation` | 14 | 50.00% | 50.00% | 7.14% | 7.14% | 14.29% | 14.29% | 14.29% |
| `privilege_scoping` | 23 | 43.48% | 43.48% | **65.22%** | 56.52% | 60.87% | 60.87% | 52.17% |
| `prompt_injection` | 14 | 85.71% | 92.86% | 100% | 100% | 100% | 100% | 100% |
| `retry_safety` | 9 | 33.33% | 33.33% | 77.78% | **100%** | 55.56% | 11.11% | 88.89% |
| `state_integrity` | 17 | 23.53% | 23.53% | **70.59%** | 64.71% | 47.06% | 29.41% | 47.06% |
| `ui_action_safety` | 8 | 25.00% | 12.50% | 0.00% | **75.00%** | 0.00% | 12.50% | **75.00%** |
| `user_consent` | 10 | 70.00% | 70.00% | 100% | 100% | 90.00% | 50.00% | 90.00% |

共性弱项：

- `input_validation` 在 4B/9B/Qwen 系列都只有 7–14%，是系统性的 `pass→repair` 偏置，需逐题诊断。
- `ui_action_safety` 只有 9B 和 Qwen4-Max 到 75%；4B/Qwen3.8-27B 为 0%，Flash 12.5%。
- `state_integrity` 4B 最高（70.59%），Qwen4-Max 47.06%，Flash 29.41%。

## 5. 部署与成本

| 模型 | 形态 | 配置 | 结果 |
| --- | --- | --- | --- |
| 0.8B | 本地 | 64 并发，context 65536 | 稳定 |
| 4B | 本地 | 第一次 64 并发/无 chunked prefill → OOM；第二次 `mem 0.50 / max 8 / chunk 2048` | 263/263 |
| 9B | 本地 | `mem 0.90 / max 4 / chunk 1024 / no cuda graph`，context 65536 | 263/263，余量约 2.4GiB |
| Qwen3.8-27B | 在线 | 4 并发，`max_tokens 1024`，`enable_thinking=false` | 263/263，157.9s |
| Qwen3.8-Flash | 在线 | 4 并发，`max_tokens 1024`，`enable_thinking=false` | 263/263，136.9s |
| Qwen4-Max | 在线 | 4 并发，`max_tokens 2048`，`enable_thinking=false` | 258/263 有效，260.4s |

在线 token 用量：

| 模型 | prompt tokens | completion tokens | 最大单题 prompt |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | 557,755 | 16,984 | 65,143 |
| Qwen3.8-Flash | 557,755 | 16,684 | 65,143 |
| Qwen4-Max | 547,475 | 16,968 | 65,154 |

## 6. 建议

| 目标 | 选择 |
| --- | --- |
| 总体/Harness 最强 | **Qwen4-Max**（78.33% / 72.11%）或 9B（76.81% / 74.21%） |
| 严格误删除门最高 | **0.8B balanced**（95.00%，但 false-allow 1） |
| 安全优先、绝不自动放行 | **Qwen4-Max**（false-allow 0，false-deny 4）或 Qwen3.8-27B（0 / 9） |
| 本地部署、无外部 API | **9B**（Harness 最强，但 gate 83.33%、false-allow 8）；4B 为训练上限 |
| 最低成本/最快迭代 | 0.8B |
| 不建议 | Qwen3.8-Flash：总体 57.41%，gate 60%，只适合“大量转人工”的保守场景 |

规模扩大没有自动解决“危险 token + 已验证安全”的正例问题；Qwen4-Max 的 4 条 false-deny 全部是 A5 安全 `cd ..`。要在本地同时拿到 9B 的 Harness 和 balanced 的门，最现实的仍是 **在 4B 上做 v5 hard-case LoRA**。

## 7. 产物

- 4B：`security/results/4b-v5/REPORT.md`
- 9B：`security/results/9b-v5/REPORT.md`
- Qwen3.8-27B：`security/results/qwen3.8-27b-v5/REPORT.md`
- Qwen3.8-Flash：`security/results/qwen3.8-flash-v5/REPORT.md`
- Qwen4-Max：`security/results/qwen4-max-v5/REPORT.md`
- 在线评测器：`security/run_openai_eval.py`、`security/openai_prompt.py`
- 本地启动脚本：`security/deploy/launch_eval_model.sh`
- 对比表：`security/results/model-size-v5/comparison.md`

## 8. 局限

- 单 seed、单次评测；在线模型快照未固定，不同时间调用可能有变化。
- Qwen4-Max 有 5 条 Harness 题格式失败（tool call / 多对象），总体 78.33% 是严格口径；有效题上 79.84%。这 5 条不在误删除门内。
- 在线模型的概率是自报值，不是 logprobs；大选项题的剩余概率是均分构造的，Brier/ECE 只能粗略比较。
- 不同模型并发不同（本地 4/2、在线 4），延迟不可直接比较。
- 9B 在 24GB 上余量很小，本次 263 题完成但不保证更高并发。
- `input_validation` 的系统性偏置尚未定位；没有评测本地 27B。
