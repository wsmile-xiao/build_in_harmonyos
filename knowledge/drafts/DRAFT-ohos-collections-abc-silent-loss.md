# DRAFT-ohos-collections-abc-silent-loss — collections 旧别名兼容：崩溃面之外，还要查 try/except 里的静默失效

> Contributor: 9CB2 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-collections-abc-silent-loss`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-libfirm-1.22.0-python312-vendored-generators` | 草稿 | py3.12 移除 `imp` 与 `collections.Mapping`，**构建期 vendored 生成器**崩溃（`ModuleNotFoundError` / `cannot import name 'Mapping'`）；修法是直接改进树内 vendored 副本 | 那条聚焦**构建时**崩溃面；本条聚焦**运行时包**，且重点是 libfirm 未覆盖的两点：①`try/except ImportError: pass` 内的**静默失效**（不报错但语义丢失）；②**是否需补丁的判据**（新名在 try 还是旧名在 try）——即"有旧名也未必该打补丁" |
| `E339` bundled Waf 2.0.x 与 `imp` 移除 | 已收录 | `imp` 模块移除导致 Waf 崩 | 同属 py3.12 兼容族，但符号与场景不同（`imp` ↔ `collections` 别名；构建工具 ↔ 运行时包）|
| `E177` `distutils.msvccompiler` | 已收录 | 构建系统层 | 无关 |

**全库查证**：对 `collections.abc` / `collections.Mapping` / `静默失效` / `分支优先级` /
`try 分支` / `except 回退` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、`knowledge/drafts/*.md`
中 grep——`collections.abc` 相关命中仅 libfirm 草稿（且见上表差异），
**"静默失效"与"分支优先级判据"两项命中 0 条**。

## Scope（何时用）

需在 Python 3.10+ 上运行的老 Python 包（2020 年前后），源码里出现
`from collections import <ABC 别名>`。

本批实例及分类：

| 库 | 位置 | 形态 | 需补丁？ |
|---|---|---|---|
| jinja2 2.10.1 | `tests.py:13`、`sandbox.py:17`、`sandbox.py:82` | ① 裸导入 → **ImportError** | ✅ 需要 |
| jinja2 2.10.1 | `runtime.py:318`、`utils.py:485` | ② 在 `try/except ImportError: pass` 内 → **静默失效** | ✅ 需要 |
| pathspec 0.6.0 | `compat.py:33/36` | 新名在 **try**、旧名在 except | ❌ **不需要** |

## Symptom

### 形态①：崩溃面（易发现）

```console
File "jinja2/tests.py", line 13, in <module>
    from collections import Mapping
ImportError: cannot import name 'Mapping' from 'collections'
/usr/local/lib/python3.12/collections/__init__.py
```

**整个包连 import 都做不到**——任何走模板渲染的代码路径全部不可用。

### 形态②：静默失效（无任何报错，最危险）

```python
# jinja2/runtime.py:316-321
# register the context as mapping if possible
try:
    from collections import Mapping
    Mapping.register(Context)
except ImportError:
    pass          # ← py3.12 在这里静默吞掉，无日志、无异常
```

程序照常运行、测试可能全绿，但 `Context` **不再注册为 Mapping**，
`LRUCache` **不再注册为 MutableMapping**——下游的 `isinstance` 判定、
鸭子类型探测、格式化/序列化路径会悄悄走不同分支。

### 反例（不该动手）

```python
# pathspec/compat.py:31-36
try:
    # Python 3.6+.
    from collections.abc import Collection as collection_type
except ImportError:
    # Python 2.7 - 3.5.
    from collections import Container as collection_type
```

新名在 **try 分支优先命中**，旧名只是低版本回退 → py3.12 上根本不会失败，
**不需要任何补丁**。

## Root Cause

Python 3.10 起 `collections` 的 ABC 旧别名（`Mapping` / `MutableMapping` /
`MutableSet` / `MutableSequence` / `Container`…）被移除，只保留 `collections.abc` 下的路径。

老库因此出现两类受损，且**第二类不产生任何错误信号**：

1. 裸导入 → `ImportError`；
2. `try: from collections import X / except ImportError: pass` 内的注册调用 →
   except 静默吞掉，**语义丢失但进程正常**。

同时必须注意：**出现旧名 ≠ 需要补丁**。真正决定是否失败的是
**分支优先级**——`collections.abc` 是在 try 里（优先命中，安全）还是在 except 里（仅回退，安全），
抑或旧名在 try 里（py3.12 直接失败）。

## Recommended Solution

### 主方案（priority 1）— `source-patch`

**先分类，再动手**：

```bash
# 1) 枚举全部旧别名引用
grep -rn "from collections import" <pkg>/ | grep -v "collections.abc"

# 2) 逐条判断：该行是否在 try 内？except 是否吞掉 ImportError？
#    - 裸导入 / try 内是旧名  → 会失败，需要改
#    - try 内已是新名        → 不会失败，不要动
```

**需要补丁时，把 try/except 内的注册点一并改**（这是本条最关键的实操点）：

```diff
 # register the context as mapping if possible
 try:
-    from collections import Mapping
+    from collections.abc import Mapping
     Mapping.register(Context)
 except ImportError:
     pass
```

只修裸导入、漏掉 try/except 内的注册点，会留下**无报错的语义丢失**——
比崩溃更难排查。补丁须用 `git apply --check` 验证（与 CI 同口径；
本机 toybox patch 对 git diff 格式会误报失败）。

### 回退方案（priority 2）— `patch-build-file`

若上游源码已冻结、不便改动，可在包内加 `sitecustomize` / 兼容 shim，
在 import 前向 `collections` 补回别名。但这会**掩盖真实的依赖问题**，
仅作最后手段。

### 禁止做法

- ❌ 只改裸导入、忽略 `try/except ImportError` 内的注册点 → 留下静默失效。
- ❌ 对已用 `collections.abc`（新名在 try）的库强行打补丁 → 无收益的改动，增加 PR 噪声与回归风险。

## 单库实证（2026-09-16）

| 库 | 处理 | 结果 |
|---|---|---|
| jinja2 2.10.1 | 5 处改 `collections.abc`（含 2 处 try/except 内），`git apply --check` 干净 | 修复前：`ImportError`，**连 import 都失败**；修复后：上游测试 **533 passed, 2 failed, 1 error, 3 skipped**（3 项为环境差异，已另条定性）|
| pathspec 0.6.0 | **不动手**（新名已在 try 分支） | 上游测试 **42 passed, 2 skipped**，零补丁 |

## 测试覆盖边界

本条只处理 `collections` 旧别名这一类符号迁移。同类但不同的移除（`imp`、`distutils`）
属其他条目（`E339` / `E177`）。另外，**静默失效形态无法靠测试发现**——
如果上游测试恰好在 py3.12 上不覆盖注册点相关语义，测试会全绿，
因此本条要求以**源码 grep + 分类**为准，而非以测试结果为准。

## 关联条目

- 相似：`E339`（`imp` 移除）、`E177`（`distutils`）、`DRAFT-ohos-pytest-host-py312-incompat`（pytest 与 py3.12 不兼容）
- 差异：见上方差异化定位表
