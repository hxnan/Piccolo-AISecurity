# AISecurity 泛化训练集 v1

第一版 LoRA 训练集，目标是把评测集要求的**安全策略判断能力**教给模型，而不是记忆评测题目。

- 数据：[ais_security_train_v1.jsonl](ais_security_train_v1.jsonl)
- 清单：[ais_security_train_v1.manifest.json](ais_security_train_v1.manifest.json)
- 生成器：[../build_training_set.py](../build_training_set.py)
- 评测集：[../ais_security_v1.jsonl](../ais_security_v1.jsonl)（**不进入训练**）

## 规模

| 项目 | 数量 |
| --- | ---: |
| 总记录 | 596 |
| train / dev | 441 / 155 |
| 中文 / 英文 | 303 / 293 |
| choice / noul / score | 348 / 218 / 30 |

| 类别 | 记录 | 覆盖内容 |
| --- | ---: | --- |
| `destructive_command` | 120 | bash / PowerShell / cmd / Python 的 `rm`、`del`、`find -delete`、`Remove-Item`、`rsync --delete`、相对路径、变量、链接、目录、镜像 |
| `authorization` | 80 | 角色、租户、审批、账号状态 |
| `prompt_injection` | 84 | 邮件/网页/扫描件/HTML 注释/文件名/客户诊断中的注入 |
| `data_egress_privacy` | 80 | 标签传播、k-匿名、直接标识符、法律保留 |
| `access_consent` | 60 | 跨团队访问、停职、不可逆 UI 操作确认、委派范围 |
| `state_ambiguity_retry` | 60 | 超时回执、重名收件人、过期缓存、版本冲突 |
| `context_audit` | 42 | 法律保留、压缩保留授权证据、审计日志 |
| `input_validation` | 40 | 闭世界契约：缺字段、未知字段、类型、枚举、互斥 |
| `action_risk_gate` | 30 | 事件影响/服务失败比例的分级评分 |

## 格式

与评测集相同的 `state` / `questions` / `labels`，额外带训练元数据：

```json
{
  "id": "tr-dc_exact-0001",
  "category": "destructive_command",
  "family": "dc_exact",
  "split": "train",
  "language": "zh",
  "difficulty": 2,
  "source": {"benchmark": "self-generated", "revision": "synthetic-v1", "license": "Apache-2.0"},
  "state": {"task": "...", "shell": "bash", "workdir": "...", "mutation_scope": "...",
            "command": "...", "session": {"env": {}, "links": {}}, "review_rules": ["..."]},
  "questions": {"decision": {"type": "noul", "instructions": "...", "criteria": {"false": "...", "true": "..."}}},
  "labels": {"decision": {"label_type": "hard", "value": true}}
}
```

- `split`：`train` / `dev`。dev 按**整个模板 family** 留出，不是按记录随机切分；dev 上的分数衡量“未见模板”的泛化。
- `family`：模板族。同一 family 不会同时出现在 train 和 dev。
- `source.benchmark = self-generated`：本仓库生成，不来自任何上游评测集。
- 标签是硬标签。训练时从标签和 `questions` 的候选键派生 one-hot 或平滑目标；训练必须走候选 token 读取与 `flex_twice` 布局，不要用通用全词表 SFT。

## 防泄漏设计

1. **模板与实体隔离**：训练使用独立项目名、路径根、人员名、文件、命令组合；不使用评测集里的 `D:\work\proj`、`cleanup_scope`、`del-zh-*` 等。
2. **不复制原题**：所有 state 由生成器按规则拼装，标签由事实机械推导，不把评测题改写后放入。
3. **选项键隔离**：训练使用 `approve/refuse/review`、`publish/merge_cell/block_export` 等任务接口键，不复用评测中的 `deny_missing_approval`、`grant_owner_exception` 等具体键。
4. **自动检查**：
   - 5-gram Jaccard 上限 0.25；本版最大 **0.0862**。
   - 命令最长公共子串上限 60 字符；本版最大 **16**。
   - 评测 ID、路径、历史命令、特有选项键均在 blocklist 中；本版拒绝数 **0**。
5. **模板级留出**：dev 是未参与训练的模板族，避免“同模板换名词”造成的虚高。

完整数值见清单的 `leakage` 字段。

## 使用建议

- 训练：`split=train`，441 条；dev 155 条用于 early stop / 选择 checkpoint，不并入训练。
- 评测集永不进入训练；增训失败样本时，也要先转成新的泛化模板，而不是直接复制评测题。
- A10 24GB：BF16 + 梯度检查点，序列 2K 即可（v1 样本 p95 为 892 字符，约 300–500 token），batch 8–16，LoRA r=16–32，冻结视觉塔；若加入长样本再升到 8K。
- 候选接口：训练目标必须与推理一致（双向 prompt attention、`flex_twice`、候选 token 读取）。
- v1 的 state 以结构化字段为主；v2 应加入自然语言工单/邮件/终端轨迹、更多领域和来自基线失败模式的新模板。

## v4：policy-free 误删除训练集

`ais_security_train_v4.jsonl` 共 **716 条**（train 533 / dev 183）：v1 的 476 条非误删除记录 + 240 条 policy-free 硬误删除记录（120 allow / 120 deny）。硬误删除的 state 只有 `task`、`shell`、`cwd`、`command`、`environment`，不含 `review_policy`/`evidence` 结论；覆盖空目录 `rm -rf`、`find` 唯一匹配、junction、hardlink、变量越界、唯一副本、UNC 等。

v4 与 v3 评测集共享模板族（Jaccard 0.4676），属于 **in-distribution 任务训练**，不是 unseen-template 泛化；D2（junction）、A3、A6、D7 是 v4 的 dev 模板。训练与复评结果见 [results/0.8b-v4/REPORT.md](../results/0.8b-v4/REPORT.md)。

## v5：中性三选一训练集

`ais_security_train_v5.jsonl` 共 **1489 条**（train 1286 / dev 203）。推荐配方是单阶段 balanced：

- v1/v2 非破坏性 train 401 条 ×2（防遗忘 replay）；
- 旧 v1 误删除 train 100 条 ×1；
- policy-free 硬误删除 192 条 ×2；
- 所有 `destructive_command` 统一为中性三选一 `allow`/`confirm`/`deny`，并移除“自动放行 / 审查规则”措辞；
- junction（d2）从 dev 移入 train，`rd /s` 受保护目录（d10）改作 dev；dev 留出模板为 a3、a6、d7、d10。

消融版 `ais_security_train_v5_compact.jsonl` 为 1088 条（885/203，非破坏性 ×1）；两阶段 stage2 为 `ais_security_v5_hard_only_d2.jsonl`。

训练：fresh base、1 epoch、LR 1.5e-5、grad accum 4、r=32 / alpha=64。复评结果见 [results/0.8b-v5/REPORT.md](../results/0.8b-v5/REPORT.md)。

## B 方案：失败驱动 v2

## B 方案：失败驱动 v2

基线跑完后：

```bash
python security/build_v2_from_failures.py \
  --scores var/eval/0.8b-baseline/scores.jsonl \
  --out-dir security/training --threshold 0.80 --scale 0.5
```

它会读取基线 `scores.jsonl`，对低于阈值的类别用新 seed 重新生成模板样本，写成 `ais_security_train_v1_v2.jsonl`；v1 的 dev 不变，v2 只进 train。生成后同样跑泄漏检查。随后用 `train_lora_peft.py` 训练合并集，`merge_adapter.py` 合并，再用同一评测脚本复评。完整命令见 [EVAL_PLAN_0_8B.md](../EVAL_PLAN_0_8B.md) 的 6.11 节。

## v1 限制

- 每条记录只有一个问题；没有评测里的多问题记录（如 `tool_call_review`）。
- state 以结构化字段为主，自然语言工单/邮件/终端轨迹较少。
- 没有专门的安全运营告警研判族（只有 `action_risk_gate` 的通用分级）。
- 样本很短（p95 892 字符），不覆盖长上下文压缩/审计场景。
- 不包含视觉/OCR 输入。
- `security_operations`、多问题轨迹和长上下文留到 v2；v2 还应优先吸收基线失败模式生成的新模板。

## 重建与校验

```bash
python security/build_training_set.py           # 重新生成
python security/build_training_set.py --check   # 校验与现有文件一致
python security/tests/test_training_set.py -v   # 结构、标签、哈希、拆分、泄漏标记
```

生成器固定 seed `20261126`，输出可复现。

## 许可

本训练集由本仓库生成，随仓库以 Apache-2.0 发布；不包含 HarnessJevBench 或 JevBench 的题目文本。
