# DRAFT-ohos-python-require-no-host-so — 纯 Python 包的可选 C 加速模块不得随 python-require 配方交付

> Contributor: 692D / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-python-require-no-host-so`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E319` 纯 Python 包打包 | 已收录 | 包在 import 期联网下载资源导致阻塞；**打包方式**用 `pip wheel --no-deps` + site-packages 布局 | E319 讲"**怎么装**"（布局/入口/联网资源）；本条讲"**什么东西不该装**"（构建机 ABI 的 `.so`）。两者可同时成立，修法完全不同 |
| `E488` notmuch2 扩展 dlopen Permission denied | 已收录 | HMDFS 上 `.so` 的 **owner/chmod** 导致 dlopen 被拒 | E488 是**权限**问题（同一机器上文件属主）；本条是 **ABI/架构绑定**（换机器即崩，与权限无关） |
| `DRAFT-multipledispatch-python-require-conan-staging` | 草稿 | 纯 Python 包在最小 Conan Python 里的 staging 打包 | 同族但问题层不同：那条讲 staging 目录与 PYTHONPATH 暴露；本条讲"编译产物不得进入产物"的具体判据 |
| `DRAFT-VENDP-PUREPY-DEP-CLOSURE` | 草稿 | 缺配方的运行依赖 vendor 进包内 | 无关（依赖闭包 vs 本包自身产物）|

**全库查证**：对 `_speedups` / `optional C extension` / `可选 C 扩展` / `pure-Python fallback` /
`纯 Python 回退` / `构建机.*ABI` / `cpython-312-aarch64` 等关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep，**命中 0 条**。

## Scope（何时用）

含**可选** C / Cython 加速模块的纯 Python 包做成 Conan 包时。
危险信号：构建机上 `pip install` / `setup.py build_ext` **编译成功**了，于是顺手把
`.so` 一起打包。

本批实例：**markupsafe 1.1.1**（`src/markupsafe/_speedups.c`）。归档内同类先例：
`yarl` / `frozenlist` / `multidict` / `aiohttp`（均走纯 Python 回退）。

## Symptom

构建机上一切正常，`conan create` 全绿；换到 ABI 或架构不同的机器上 import 即崩：

```console
ImportError: /path/markupsafe/_speedups.cpython-312-aarch64-linux-ohos.so:
             wrong ELF class
# 或
ImportError: undefined symbol: PyUnicode_FromString
# 或
ImportError: module compiled against API version 0x… but it requires 0x…
```

典型形态是"**本地过、他机崩**"：构建机自己跑测试 100% 通过，因此在 CI 上毫无征兆。

## Root Cause

`pip install` / `build_ext` 产出的扩展模块名自带构建机解释器标签：

```
markupsafe/_speedups.cpython-312-aarch64-linux-ohos.so
                       ^^^^^^^^^^^ ^^^^^^ ^^^^^^^^^^^^^^
                       CPython ABI 架构   平台
```

它绑定**构建时**的 CPython ABI 版本与目标架构。打进 `python-require` 包后有双重放大：

1. `python-require` 包**不参与 Conan 的二进制兼容性计算**——坏产物无法被依赖图拦住；
2. Conan 缓存会把该包传播到别的配置/平台，失败现场与根因距离极远。

**而这类模块本就通常是可选加速**——上游以 `try/except ImportError` 回退纯 Python：

```python
# markupsafe/__init__.py (1.1.1)
try:
    from ._speedups import escape, escape_silent, soft_unicode
except ImportError:
    from ._native import escape, escape_silent, soft_unicode
```

yarl（`_quoting_c` ↔ `_quoting_py`）、frozenlist、aiohttp 同理。纯 Python 回退功能等价：
markupsafe 1.1.1 实测 **32 passed / 11 skipped**，跳过项正是上游按 `skipif` 规则跳过的
`_speedups` 组——**不是失败**。

## Recommended Solution

### 主方案（priority 1）— `package-pure-python-fallback`

只打包纯 Python 源码：`package()` 跳过 `*.c` / `*.h` / `*.pyx` 与任何 `*.so`，
仅交付 `.py`；上游的 `try/except ImportError` 会自动走回退路径。

```python
for entry in sorted(os.listdir(src)):
    if entry.endswith((".c", ".h", ".pyx", ".so")):
        continue                      # 可选加速源码/产物一律不交付
    shutil.copy2(os.path.join(src, entry), os.path.join(pkg_dir, entry))
```

口径与归档内既有同类包（`yarl` / `frozenlist` / `aiohttp`）一致，并在 docstring /
`notes.md` 写明"上游 C 加速是可选，此处刻意走纯 Python 回退"，避免后人误以为漏打产物。

### 回退方案（priority 2）— `conan-managed-extension-build`

若纯 Python 回退在功能或性能上**确实**不可接受，正确做法是让扩展**由 Conan 在消费方
目标平台重新编译**（`tool_requires` 目标解释器 + 目标 toolchain），而不是复用构建机产物。

### 禁止做法

- ❌ `pip install --target <staging> .` 后把 staging 里的 `*.so` 一起 `copytree` 进 `site-packages`。
- ❌ 为构建可选加速而在配方里引入 `Cython` / `cython`——上游已提供纯 Python 回退，属过度工程，还会把构建工具拖进依赖闭包。

## 单库实证

| 库 | 处理 | 结果 |
|---|---|---|
| markupsafe 1.1.1 | `package()` 跳过 `.c`/`.h`，交付 4 个 `.py` | `conan create` 绿；上游 32 passed / 11 skipped；消费者测试断言 `_native` 回退行为（escape/Markup/`soft_unicode` 契约）全部通过 |

> 对照：本机（aarch64 OHOS 原生）实测 `_speedups` **能**编译成功
> （产出 `_speedups.cpython-312-aarch64-linux-ohos.so`）——正因"能编译"才更需要本条约束：
> 编译成功 ≠ 可以交付。

## 测试覆盖边界

本条不解决"纯 Python 回退与 C 加速的行为差异"。若某些行为仅 C 版本提供（上游未在
`_native` 实现），则回退方案不完整，须走 fallback 方案在目标平台编译扩展。

## 关联条目

- 相似：`E319`（纯 Python 包打包方式）、`E488`（扩展 dlopen 权限）
- 差异：见上方差异化定位表
