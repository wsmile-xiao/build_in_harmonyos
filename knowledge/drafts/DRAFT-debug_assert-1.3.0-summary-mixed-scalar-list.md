# DRAFT-debug_assert-1.3.0-summary-mixed-scalar-list - summary.py 同一 manifest key 先标量后列表导致 `str` append 崩溃

> **Contributor**: junshi_liu（兰州大学DSLab）| **Status**: DRAFT | **Updated**: 2026-08-31
> **Severity**: medium | **Category**: framework / parsing / yaml / summary
> **来源**: debug_assert 1.3.0 HarmonyOS PC 本地交付前验证（R05 实测），路径 B 知识库扩展候选
> **结构化数据**: [drafts/DRAFT-debug_assert-1.3.0-summary-mixed-scalar-list.kv](DRAFT-debug_assert-1.3.0-summary-mixed-scalar-list.kv)

## 错误特征

```
ohc-run.py summary 输出:
  SUMMARY.md 生成失败: 'str' object has no attribute 'append'
  rc=1
Traceback（最小复现）:
  File ".../scripts/ohc/summary.py", line 89, in _parse_yaml_simple
    data.setdefault(current_list_key, []).append(item)
AttributeError: 'str' object has no attribute 'append'
```

## 最小复现（R05 实测，2026-08-31）

- 触发命令: `python3 scripts/ohc-run.py summary --project-dir <worktree>`
- 触发 manifest: `archives/q/qpdf/12.3.2/manifest.yaml`（以及 `12.3.2.1`）
- 根因位置: `scripts/ohc/summary.py` `_parse_yaml_simple()`，当同一 YAML key 先被解析为
  标量（`key: value`，`data[key] = str`），后被同一 key 的列表项（`- item`）追加时，
  `data.setdefault(current_list_key, [])` 返回已存在的字符串，对其调用 `.append()` 即崩溃。

## 根因

`_parse_yaml_simple()` 用 `data.setdefault(current_list_key, [])` 假定某 key 首次出现
就是列表；但当 manifest 中同一 key 先以标量形态、后以列表形态出现（或解析器状态机把
同一 key 先后归入不同分支）时，`data[key]` 已是 `str`，`setdefault` 不会覆盖，
`.append` 对 str 调用抛 `AttributeError`。

## 解决方案

在追加列表项前防御性地确保目标是 list：

```python
_lst = data.get(current_list_key)
if not isinstance(_lst, list):
    _lst = []
    data[current_list_key] = _lst
_lst.append(item)
```

R05 临时修复前后 SHA-256：`d4d14df2…62a` → `d4cc5892…80a`（SUMMARY.md 生成成功，
373916 字符）；验证后已 `git checkout --` 恢复至 `d4d14df2…62a`，框架零残留。

## 验证

- 修复前: `ohc-run.py summary` rc=1（`str object has no attribute append`）
- 修复后: `ohc-run.py summary` rc=0，`SUMMARY.md 生成完成 (373916 字符)`
- 恢复后: `scripts/ohc/summary.py` SHA-256 与修复前一致，`git status` 无残留

## 适用边界

适用于所有依赖本仓库 `scripts/ohc/summary.py` `_parse_yaml_simple()` 的
`ohc summary` / `finish` step[8/10] gen_summary 流程。当任意 `archives/**/manifest.yaml`
中同一 key 以标量+列表混合形态出现时会触发；修复后各库在 summary 生成阶段不再因此失败。
不改变解析结果语义（仍按列表收集），仅避免 str 上调用 append 崩溃。
