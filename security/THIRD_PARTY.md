# AISecurity 数据集来源与许可

`ais_security_v1.jsonl` 是以下两个公开基准数据集的筛选合并。上游数据均为 MIT 许可，本目录保留来源、固定 revision 与完整许可声明。

## HarnessJevBench

- 仓库：<https://github.com/agentscope-ai/HarnessJevBench>
- revision：`50ed12899b4767392a2ad8cb515599f049f7bd9d`
- 使用文件：`benchmark/records.jsonl`
- 使用范围：16 个安全控制 scenario 中带 `hard` 标签的题目
- 数据许可：MIT（见上游 `LICENSE.md`）

MIT License

Copyright (c) 2026 HarnessJevBench contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## JevBench

- 仓库：<https://github.com/fstandhartinger/jevbench>
- revision：`609a664e81f46e03731600bd7bd9f1b7a61257c5`
- 使用文件：`datasets/public/original.jsonl`、`easy.jsonl`、`hard.jsonl`
- 使用范围：逐题复核后纳入的 13 条安全相关题目（见清单 `selection.jevbench`）
- 数据许可：MIT（每条记录 `provenance.license` 亦标记为 MIT）

MIT License

Copyright (c) 2026 Florian Standhartinger and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 本地改动

- 合并、字段重命名（`source`、`category`、`labels`）以及只保留 `hard` 标签属于本仓库的整理工作。
- 题目文本与选项未改写；`state`、`questions` 保留上游内容。
- 评测集不包含上游的 Soft 概率视图、参考推导或未选中的题目。

## 自扩展用例

`extended/deletion_guard_v1.jsonl` 中的 30 条误删除命令用例（中英文各 15 条，难度 1–15）由本仓库编写，不使用上游题目文本，随本仓库以 Apache-2.0 发布。它们与两个基准数据集分开标记：`source.benchmark` 为 `self-extended`，`source.revision` 是该文件的 sha256。
