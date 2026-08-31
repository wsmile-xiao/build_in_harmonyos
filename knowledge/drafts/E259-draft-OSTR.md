# E259 - control-plane 纯逻辑测试的 ServiceAction 定义顺序问题可用 recipe patch 修复

> **结构化数据**: [E259-draft-OSTR.kv](E259-draft-OSTR.kv)
> **类别**: testing/import-order/review | **严重度**: 🟡 | **阶段**: testing/review

## 症状
`pytest tests/test_models.py` 在收集阶段就报 `NameError: name 'ServiceAction' is not defined`。

## 根因
`ServiceStatus.allowed_actions` 在 `models.py` 中引用了 `ServiceAction`，但 `ServiceAction = Literal[...]` 定义在 `ServiceStatus` 之后。Python 3.12 导入时会立刻求值注解。

## 修复
把 `ServiceAction = Literal[...]` 提前到 `ServiceStatus` 等模型之前，并通过 Conan recipe 的 `apply_conandata_patches()` 在 source 阶段应用补丁。

## 验证
- `PYTHONPATH=src python -m pytest tests/test_models.py tests/test_config.py -q`：5/5 PASS
- 详细模式复核：`test_models.py` 3 个用例 PASS，`test_config.py` 2 个用例 PASS

## 关系
- `similar_to -> E257, E258`
- 这条关注的是 upstream 控制面纯逻辑测试的导入顺序；修复后可把 review 要求的 pure-logic 子集计入已执行通过项。
