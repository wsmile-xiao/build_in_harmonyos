# draft-interrogate-1.7.0-tabulate-010-fixture-widening

## 症状

`conan create` 的上游套件里，五个 verbosity=2 的 expected-output 对比用例失败，其余全绿：

```
FAILED tests/functional/test_coverage.py::test_print_results[2-expected_detailed.txt]
AssertionError: assert '------------------------------ Detailed Coverage -----...' in
'= Coverage for .../sample/ =\n-----...100.0% |...'
 +  where CaptureResult(out='...') = capsys.readouterr()
5 failed, 223 passed, 13 skipped
```

失败内容细看**语义全对**（行名、数字、百分比、PASSED/FAILED 状态全一致），只有表格每列宽了 2 字符。

## 根因

tabulate 0.10.0 把每个单元格的左右 padding 从 0 改为 1 空格，列分隔线随之 +2。上游 interrogate 1.7.0 的 `tests/functional/fixtures/expected_*.txt` 按 tabulate 0.9.x 列宽生成，`assert expected_out in captured.out` 的子串匹配对列宽敏感——内容对、宽度错，照样判失败。属于"上游 fixture 冻结了旧版依赖的渲染细节"类版本漂移，不是适配缺陷。

对照实验（同一 staged 树，仅换 tabulate 版本）：

- tabulate 0.10.0（registry 版）：5 failed / 223 passed
- tabulate 0.9.0（PyPI wheel 钉版）：228 passed / 13 skipped，Detailed 表格渲染与 fixture 逐字节一致（diff 仅剩 verbosity=2 正常多出的 Summary 段）

## 解决

1. **套件侧钉版**：按 pytest/9.1.1 `_SUITE_WHEELS` 手法，URL+sha256 精确锁定 `tabulate-0.9.0-py3-none-any.whl`，`pip --target` 装进构建期 test-deps——把 index 的版本选择权收走，保证可复现。
2. **registry 依赖不降级**：`requires("tabulate/0.10.0")` 保持仓内已有版本（0.9.0 不在仓，PF4 必拦私自捎带）。
3. **两段分工**：套件测 fixture 保真（0.9.0），test_package 用 registry 0.10.0 驱动真实 CLI 验证功能面（fail-under 退出码、badge 生成、表格可渲染）。
4. **PYTHONPATH 次序**（配套 DRAFT-interrogate-1.7.0-conan-env-prepend-order）：钉版 wheel 的 test-deps 必须压在 registry 依赖路径之前。

## 验证

```
# 复现（0.10.0）：5 failed, 223 passed, 13 skipped
# 修复（钉 0.9.0）：228 passed, 13 skipped in 1.67s
# 渲染对照：diff <(渲染输出) tests/functional/fixtures/expected_detailed.txt  →  仅 Summary 段差
```

## 迁移建议

- 任何"文本 fixture + 表格渲染库"的 Python 件，先做渲染库版本对照实验再判定失败归属。
- 钉版 wheel 的 sha256 取自 PyPI JSON API，conandata/配方内常量双处可复核。
