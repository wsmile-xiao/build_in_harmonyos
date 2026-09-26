# zope.interface 8.6 — 上游测试报告（R51 三步法）

## 测试清单（第一步：清点）

- 位置：`zope.interface-8.6.tar.gz`（SHA256 核验
  `b40ef9b4873afb5d0dec02b8d2dfde1cf18c72337b60c99cb735961e0bac05c0`）
  → `src/zope/interface/tests/`
- 18 个 unittest 测试模块：test_adapter.py、test_advice.py、
  test_compile_flags.py、test_declarations.py、test_document.py、
  test_element.py、test_exceptions.py、test_interface.py、
  test_interfaces.py、test_odd_declarations.py、test_registry.py、
  test_ro.py、test_sorting.py、test_verify.py + tests/__init__.py
  （OptimizationTestMixin/SubclassableMixin）
- 测试框架：pytest 9.1.1（unittest 风格，无 pytest 专有 fixture）。
- 测试期依赖：zope.testing 6.2（test_ro.py 硬依赖
  `zope.testing.renormalizing`；tests/__init__.py 对 zope.testing.cleanup
  为 try/except 可选）。

## 实测（第二步：可运行环境运行）

命令（从 SHA256 核验过的 sdist 解压目录运行）：

```bash
cd zope.interface-8.6
PYTHONPATH=src PURE_PYTHON=1 python3 -m pytest src/zope/interface/tests/ -q
```

结果：

```
1131 tests collected
1131 passed in 1.59s
```

- **实测：pass_1131_skip_0（通过率 100%，路径A）**
- 声明数核对：无上游官方"声明数"；以 pytest 实际收集数 1131 为准。
- 环境：python3 3.12.9（本机）、pytest 9.1.1、zope.testing 6.2。

### 关于 9 个 C 优化测试的如实说明

默认模式（不设 PURE_PYTHON）下 9 个 `test_optimizations` 用例失败
（test_declarations.py ×3、test_interface.py ×2、…共 9）。原因：

- `tests/__init__.py` 的 `OptimizationTestMixin.test_optimizations` 按
  `_should_attempt_c_optimizations()` 决定断言：应尝试 C 优化时断言
  `used is not fallback`（C 实现在用），否则断言 `used is fallback`。
- 本包**纯 Python 打包、不携带 C 扩展**，默认模式下 `_should_attempt_...`
  返回 True（无 PURE_PYTHON、非 PyPy），断言要求 C 实现在用 → 失败。
- 设 `PURE_PYTHON=1` 后 `_should_attempt_c_optimizations()` 返回 False，
  断言转为 `used is fallback` → 9 个用例全部通过。

`PURE_PYTHON=1` 正是**本包的部署形态**（纯 Python 回退），也是上游自己
纯 Python CI job 的运行方式（`_compat.py` 文档明确）。因此
`pass_1131_skip_0` 是真实、可复现的；9 个 C 优化用例的失败仅存在于"应使用
C 扩展但未携带"的配置下，属平台/构建形态限制而非功能回归。若未来需要
C 扩展加速，按 build-systems.md §14 交叉编译并回填。

## 与声明数核对（第三步：PR 回填）

| 项 | 值 |
|---|---|
| 收集（声明） | 1131 |
| 实测通过 | 1131 |
| 实测跳过 | 0 |
| 实测失败 | 0 |
| 通过率 | 100%（1131/1131，路径A） |
