# Piccolo AISecurity 工作计划

- 记录日期：2026-11-26
- 目标：以 Piccolo-0.8B-VL（固定 revision `3af36a7c`）为基线，构建 AI security 评测集，完成评测、LoRA 增训、复评与报告。详细执行方案见 [EVAL_PLAN_0_8B.md](EVAL_PLAN_0_8B.md)。
- 状态图例：`待开始` / `进行中` / `已完成` / `受阻`

## 总览

| # | 步骤 | 产出 | 状态 |
| --- | --- | --- | --- |
| 1 | 合并 HarnessJevBench 与 JevBench Public 的 AI security 用例 | v5：`security/ais_security_v5.jsonl` + 清单（v1–v4 保留） | 已完成 |
| 2 | 在阿里云 GPU 主机评测 0.8B-VL，建立能力基线 | v5 基线 56.27%（148/263）；误删除 58.33% | 已完成 |
| 3 | 针对基线失败用例生成泛化训练集，做 0.8B LoRA 增训 | v5：1489 条（1286/203）；balanced fresh LoRA | 已完成 |
| 4 | 用同一评测集复评增训模型并与基线对比 | v5：65.02%；Harness 54.21%；误删除 95.00%（基线 58.33%） | 已完成 |
| 5 | 总结并输出效果报告 | [v1](results/0.8b-lora-v1/REPORT.md) · [v3](results/0.8b-v3/REPORT.md) · [v4](results/0.8b-v4/REPORT.md) · [v5](results/0.8b-v5/REPORT.md) | 已完成 |
| 6 | 对比 0.8B / 4B / 9B / Qwen3.8 / Qwen4 在 V5 上的表现 | [模型对比](results/model-size-v5/REPORT.md) · [4B](results/4b-v5/REPORT.md) · [9B](results/9b-v5/REPORT.md) · [Qwen3.8-27B](results/qwen3.8-27b-v5/REPORT.md) · [Qwen3.8-Flash](results/qwen3.8-flash-v5/REPORT.md) · [Qwen4-Max](results/qwen4-max-v5/REPORT.md) | 已完成 |

## 1. 构建 AISecurity 评测集

- 当前版本 v5：与 v3 相同的 255 条记录，只改自扩展的 60 条误删除题，问题改为中性三选一 `allow`/`confirm`/`deny`；Harness/JevBench 原文不动。
- 来源（固定 revision，随清单记录）：
  - HarnessJevBench `50ed12899b4767392a2ad8cb515599f049f7bd9d`，`benchmark/records.jsonl`，选 182 条（目标 180）
  - JevBench Public `609a664e81f46e03731600bd7bd9f1b7a61257c5`，`datasets/public/{original,easy,hard}.jsonl`，逐条复核选 13 条
  - 自扩展：v5 为 60 条 policy-free 硬误删除用例（30 allow / 30 deny），输入只含任务、shell、cwd、命令和原始环境文件；v1–v3 保留作历史对照
- 口径：
  - 基准只用 `hard` 标签；上游 Soft 概率标签不混入能力基线。
  - Harness 按 scenario 整体纳入 18 个安全/操作安全场景。
  - JevBench Public 没有 security family，按题目逐条复核后以 ID 白名单纳入访问控制、隐私合规、安全运营与注入对抗用例。
  - 每条记录用 `source.benchmark` 区分 `HarnessJevBench`、`JevBench` 或 `self-extended`。
  - **编辑范围**：只允许改自扩展用例和训练集；开源基准用例逐字节保留。
- 验收：ID 唯一、标签可映射、来源 revision 可校验、内容哈希可复现。
- 构建脚本：`security/build_dataset_v5.py`；校验：`python security/tests/test_dataset_v5.py -v`。

## 2. 云主机基线评测

- 模型：Piccolo-0.8B-VL，revision `3af36a7cc6cc041f99fb674de331fdded96eee0`；BF16 全量 checkpoint，只走文本 `flex_twice` 路径。
- 前置信息（不入库）：主机地址、SSH 方式、GPU 型号与数量、镜像、模型权重目录、服务端口。
- 部署：官方 SGLang 插件 + `/v1/systemone`，主路径 H100/FA3，省钱路径 L20/FlashInfer；启动参数与质量闸门见 [EVAL_PLAN_0_8B.md](EVAL_PLAN_0_8B.md)。
- 评测：`security/run_eval.py` 逐题请求，原始响应先落盘；记录概率、argmax、延迟与 usage。
- 基线指标：总体/分来源/分类别准确率、noul 校准（Brier/ECE）、无效输出率、自扩展 false-allow、逐题失败清单。
- 约束：固定 revision、prompt 布局、温度与上下文上限；不做截断；超限题单列。

## 3. 泛化训练集与 LoRA 增训

- 训练集 v1 已生成：`security/training/ais_security_train_v1.jsonl`（596 条，train 441 / dev 155），覆盖误删除命令、授权、注入、数据外泄、访问确认、状态歧义、上下文审计、参数校验与风险分级。生成方法与防泄漏阈值见 `security/training/README.md`。
- 对基线失败用例聚类（按类别与失败模式），区分“知识缺口”与“布局/校准问题”。
- 基于失败模式生成泛化样本，而不是复制评测原题；评测集不进入训练集。
- 训练：0.8B-VL 的 LoRA（目标模块、r/alpha、学习率、epoch、序列长度）在云主机执行，记录配置、耗时与显存。
- 产物：训练集、适配器权重、训练日志；数据与权重不提交到源码仓库。

## 4. 复评与对比

- 同一评测集、同一推理配置复评增训模型。
- 对比：总体与分类准确率、无效输出率、校准变化、逐题翻转（修正/退化）；`score_eval.py --baseline-scores` 直接输出 fixed/regressed。
- 报告同时列出“提升”和“回退”，不只报总体分数。

## 5. 报告

- 内容：数据构成、基线、训练配方、复评结果、失败模式分析、局限与复现方式。
- 报告中的数字必须来自实际运行结果；未执行的步骤明确标注未完成。

## 执行原则

- 不伪造、不外推未测量的分数；不把训练样本或历史轨迹当作发布模型成绩。
- 训练集、评测集、权重、日志分离；评测集固定后再开始增训。
- 不提交凭据、主机信息、日志或 checkpoint；云主机操作仅记录非敏感配置。
- 保留上游 MIT 数据来源与许可说明（见 `security/THIRD_PARTY.md`）。
