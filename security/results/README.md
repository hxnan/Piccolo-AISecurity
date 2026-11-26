# AISecurity 评测结果归档

每个版本目录（`0.8b-lora-v1/`、`0.8b-v3/`、`0.8b-v4/`、`0.8b-v5/`）保存两类结果：

- 顶层：`*.summary.json`、`*.summary.md`、`*.scores.jsonl`、`*.run.json`，以及训练配置/日志和 `REPORT.md`。
- `raw/`：**原始评测输出**，不是只有统计数字。

## `raw/` 内容

| 文件 | 说明 |
| --- | --- |
| `<label>.raw.jsonl` | `/v1/systemone` 的逐题原始响应：`answer`、`response`、`evaluation_trace`、usage、延迟、状态码 |
| `<label>.scores.jsonl` | 逐题评分（expected / predicted / 概率 / Brier / 正确性） |
| `<label>.failures.md` | 失败题清单 |
| `<label>.summary.md` | 可读汇总 |
| `<label>.run.json` | 模型名、数据集 sha256、端口、并发、时间等运行元数据 |
| `MANIFEST.json` | 每个文件的大小与 sha256，用于校验归档完整性 |

`var/eval/` 是评测时的本地工作目录，已被 `.gitignore` 忽略；`security/results/*/raw/` 才是项目内归档。两者的 `raw.jsonl` 内容一致。

服务端 SGLang 日志和模型 checkpoint 按项目约定不纳入归档，保留在云主机 `/opt/piccolo/var/` 与 `/models/`。

## 已归档的 run

### v5（当前）

- `baseline`：`piccolo-0.8b-vl` on `ais_security_v5.jsonl`
- `balanced`：推荐模型 `piccolo-0.8b-vl-lora-v5-balanced`
- `single`：消融 `piccolo-0.8b-vl-lora-v5-single`
- `two_stage_d2`：消融 `piccolo-0.8b-vl-lora-v5-ts-d2`
- `fresh_v5_replay3x`、`repair`、`two_stage_1ep`、`two_stage_2ep`：中间实验

### v3

- `baseline`、`lora-1ep`

### v4

- `baseline`、`lora-v4`

### v1

- `baseline`、`lora-1ep`、`lora-3ep`

## 校验

```bash
python - <<'PY'
import hashlib, json
from pathlib import Path
root = Path("security/results/0.8b-v5/raw")
manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    for key, meta in entry.items():
        if not isinstance(meta, dict):
            continue
        path = root / meta["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == meta["sha256"], path
print("raw archive OK")
PY
```
