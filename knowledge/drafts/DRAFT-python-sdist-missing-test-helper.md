# DRAFT — 纯 Python 包的 sdist 可能**不含**测试辅助文件；且 tests/ 会在**模块级**构造对象，收集期即需可选 extra

> 触发事件：construct 2.10.70 HarmonyOS PC 适配（PR #12205）。`conan create`
> 的上游测试步骤先在收集期全挂、修复后又暴露出一个清单外失败（2026-09-23/24 真机实测）。

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-pypi-wheel-vendor-python-dep-closure`（`{.kv,.md}`） | 草稿 | PyPI 包装配时需**自带**纯 Python 依赖闭包（把依赖一起 vendor 进 wheel） | 本条讲的是**测试辅助文件不在 sdist 里**（上游 `MANIFEST.in` 少收），以及**收集期**就需可选 extra；属「sdist 内容不全 / 收集期依赖」，与「要不要 vendor 依赖闭包」不同层 |
| 对 `tests.declarativeunittest` / `MANIFEST.in` / `收集期 import extra` 的 E 编号检索 | — | `knowledge/graph/index.tsv` 与 `E*.kv` **0 命中** | 本条为真增量；同族仅上述草稿一条，已在 `similar_to` 中标注 |

## 错误特征

**第一层（辅助文件缺失，5 个测试文件全部收集失败）**：

```
ModuleNotFoundError: No module named 'tests.declarativeunittest'
ERROR tests/test_core.py
ERROR tests/test_compiler.py
ERROR tests/test_expr.py
ERROR tests/test_benchmarks.py
ERROR tests/test_multiprocessing.py
```

而 `ls tests/` 只有 `test_*.py` —— **没有** `declarativeunittest.py`。

**第二层（收集期就 import 可选 extra）**：

```
ModuleNotFoundError: No module named 'arrow'
```

发生在**收集期**（不是某个用例内部）——因为 `tests/` 在**模块级**构造
`Timestamp(...)`，而该适配器的构造函数里 `import arrow`。

## 根因分析

### 要点 1：PyPI sdist 的 `MANIFEST.in` 可能只收少数文件

construct 2.10.70 的 sdist 内 `MANIFEST.in` 仅两行：

```
include README.rst
include LICENSE
```

因此 `tests/declarativeunittest.py`（5 个测试文件都 `from tests.declarativeunittest
import *`）**根本没进 sdist**。这是**上游打包问题**，不是本仓配方的错。

### 要点 2：模块级构造 → 收集期就需要可选 extra

`Timestamp` 是 construct 的**可选**适配器（extra `arrow`）。测试在模块级构造它，
于是 pytest 一收集该文件就 `import arrow` —— 失败**发生在收集期**，
表现为「整个文件 ERROR」而非「某些用例 failed」。

### 要点 3：纯 Python 包的这类失败很容易被「本地绿」掩盖

本机若恰好装了 `arrow` / `ruamel.yaml`，收集期与用例都通过 ——
**本地绿、CI 红**。必须区分「本机有」与「配方声明了」。

## 推荐方案

1. **辅助文件**：构建期从**上游固定 tag** 的 raw URL 取回缺失文件，并在取不到时
   **显式失败**（不静默跳过）：
   ```python
   MISSING = ("https://raw.githubusercontent.com/construct/construct/v2.10.70/"
              "tests/declarativeunittest.py")
   # 取不到 → raise ConanException（R51：拒绝在未跑套件的情况下报告通过）
   ```
   固定 tag 而非 `master`，避免上游漂移。
2. **可选 extra**：构建期补装测试真正需要的 extra（本包：`arrow`、`cloudpickle`、
   `ruamel.yaml`）。对带 C 扩展的 extra（`ruamel.yaml.clib`）用
   `pip install --no-deps <pkg>` —— 纯 Python 模式足够。
3. **申报口径**：允许清单/豁免必须逐项写清**为什么**（哪个 extra、哪条路径），
   并让构建日志显式告警。

## 禁止做法

- ❌ **不要**因为 `ls tests/` 里没有辅助文件就断定「上游没有测试」——先确认
  sdist 与上游仓库的差异（`MANIFEST.in` 是常见元凶）。
- ❌ **不要**把「收集期 ERROR」当成「用例失败」处理：二者成因完全不同
  （前者是 import/依赖，后者是断言）。
- ❌ **不要**只在本地跑通就判定配方无误 —— 本机恰好装了可选 extra 会造成假绿。

## 验证证据

- **主证据**：construct 2.10.70（PR #12205）真机实测。
  - 未取回辅助文件 → 5 个测试文件收集期全挂（`No module named 'tests.declarativeunittest'`）。
  - 取回（2014 字节，带 3 次重试）后 → 进入正常执行。
  - 未装 `arrow` 时 `test_benchmarks`/`test_compiler` 收集期报 `ModuleNotFoundError: 'arrow'`；
    装上后消失。
  - CI #59707 又暴露 `test_exportksy` 缺 `ruamel` → 补装后该项真实通过。
  - 最终本地口径：`181 passed / 4 failed / 13 xfailed`（4 项为 numpy/lz4 可选 extras 缺失，已逐项列入允许清单）。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / conan 2.29.1。

## 查重结论

- 对 `tests.declarativeunittest` / `MANIFEST.in` 与「sdist 缺测试辅助文件」检索：**0 命中**。
- 对「模块级构造导致收集期需要可选 extra」检索：无同机制条目；本仓既有条目多为
  运行期依赖/链接路径问题，与「sdist 打包不全 + 收集期 import extra」路径不同。
- **盲区声明**：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人
  提交过同主题草稿。
