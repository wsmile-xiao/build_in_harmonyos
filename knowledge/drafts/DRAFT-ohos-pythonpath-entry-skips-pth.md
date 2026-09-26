# DRAFT-ohos-pythonpath-entry-skips-pth — PYTHONPATH 上的包目录不执行 `.pth`：「import setuptools 成功」≠「distutils 可用」

> Contributor: 3211 / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-pythonpath-entry-skips-pth`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E512` 纯 Python 包 build() 自检 import 运行时包，宿主预装而 CI 缺失 → 本地过、CI 挂 | 已收录 | **依赖缺失**导致 `ModuleNotFoundError`，修法是 `add-deps`（把缺的包声明为依赖） | E512 是「**根本没这个包**」；本条是「**包在、顶层可 import，但它补充的二级模块因 .pth 未执行而缺失**」——补依赖**不能**解决（因为 pip 会认为已满足）。两者都表现为 ModuleNotFoundError，但**诊断方向相反**：E512 去补包，本条要去掉 PYTHONPATH 供给改为真装 |
| `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` | 草稿 | 子进程 env **整体覆盖** PYTHONPATH → 注入失效，须改独立 venv | 那条是 PYTHONPATH「传不进去」；本条是 PYTHONPATH「传进去了但语义不完整」（只加 sys.path，不执行 .pth）。两条会在同一测试环境里同时出现：前者要求用 venv，后者要求**别**把引导目录塞进 PYTHONPATH —— 结论互补而非重复 |
| `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable` | 草稿 | 源码直拷无 `.dist-info` → `importlib.metadata` 抛 PackageNotFoundError | 同属「包元数据/附加物在直拷或 PYTHONPATH 供给下丢失」，但那条丢的是**发行版元数据**（`.dist-info`），本条丢的是 **`.pth` 的注册副作用**。两条共同说明：**「把包目录放上去」与「真正安装」不等价**，直拷式打包的附加物有多种形态 |

**全库查证**：对 `distutils-precedence`、`.pth 不执行`、`PYTHONPATH.*pth` 三组关键词在 `knowledge/drafts/*.kv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md` 中检索，**命中 0 条**。

## Scope（何时用）

| 信号 | 检查命令 |
|---|---|
| 用 `pip install --target <dir>` 引导依赖，再以 `PYTHONPATH=<dir>` 供给测试环境 | 检查搭建方式 |
| 出现 `No module named 'distutils'`（Python 3.12+） | 直接观察报错 |
| 现象**只在嵌套 venv / 子解释器**里出现，主进程正常 | 观察报错位置 |
| 子 venv 里 `pip install setuptools` 报 `Requirement already satisfied` 但该 venv 无 setuptools 目录 | `<venv>/bin/python -m pip install setuptools` |

## Symptom（真实表现）

cffi 2.1.1 适配中，把构建期 setuptools 引导目录放进测试 `PYTHONPATH` 后：

```
testing/cffi0/test_zintegration.py ...... 7 项 ERROR
E   ModuleNotFoundError: No module named 'distutils'
```

而**主测试进程**里 `import setuptools` 明明是成功的 —— 这正是最迷惑人的地方。

### 「半可见」的验证

```bash
$ PYTHONPATH=<boot> python3 -c "import setuptools; print(setuptools.__file__)"
<boot>/setuptools/__init__.py          # ✅ 顶层包可见

$ PYTHONPATH=<boot> python3 -c "import distutils"
ModuleNotFoundError: No module named 'distutils'   # ❌ .pth 未执行
```

## Root Cause

CPython 启动时只对**真正的 site-packages 目录**（经 `site.addsitedir` 处理）执行其中的 `.pth`；**PYTHONPATH** 加入的目录只进 `sys.path`，**不触发 `.pth` 处理**。

以 setuptools 为例，Python 3.12+ 已把 `distutils` 移出 stdlib，完整供给依赖：

```
setuptools/distutils-precedence.pth   →   安装 _distutils_hack，
                                          把 setuptools._distutils 注册为 distutils
```

该 `.pth` 未执行 → `distutils` 不存在。

### 为什么只在嵌套 venv 里爆

被测套件（cffi 的 `test_zintegration`）会在**嵌套 venv** 里重新构建。子 venv 的 pip 因为能从继承的 PYTHONPATH 看到 setuptools，报 `Requirement already satisfied` 而**跳过安装** —— 于是那个 venv 的 site-packages 里从未装入 setuptools，自然也没有 `.pth`，构建后端 import distutils 立即失败。

**三重隐蔽性**：① 主进程正常；② 报错在子环境；③ pip 明说「已满足」，误导排查方向。

## Recommended Solution

### 首选：让每个环境自己真正安装

**不要**用 PYTHONPATH 提供需要 `.pth` 才能完整的包。改为：

```python
# conanfile.py 的测试环境搭建
# ① 主测试 venv：真正安装
<venv>/bin/python -m pip install setuptools
# ② 关键：从测试 PYTHONPATH 中**移除**引导目录，不向子环境泄漏
paths = [shimmod, src, os.path.join(src, "src"), test_deps]   # 注意：不含 setuptools 引导目录
```

这样嵌套 venv 会各自正常安装 setuptools（不再被「already satisfied」误导），`.pth` 正常执行。

**cffi 实测效果**：zintegration **7 项 ERROR → 8 passed**。

### 备选（priority 2）：显式模拟被跳过的 `.pth` 效果

确实必须用 PYTHONPATH 供给时（离线等），显式补出等价注册：

```python
# sitecustomize 内
import setuptools._distutils, sys
sys.modules.setdefault("distutils", setuptools._distutils)
```

> 此路更脆：须随上游 `.pth` 内容变化同步维护，属**模拟**而非真装，仅在首选不可行时使用。

## 反面模式（forbid）

| 模式 | 为什么禁止 | 后果 |
|---|---|---|
| 看到 `import setuptools` 成功就认定「distutils 可用」 | `.pth` 在 PYTHONPATH 目录上不执行；Python 3.12+ 的 distutils 完全依赖该 `.pth`，两者必须分别验证 | 测试环境「看起来齐备」，一到嵌套 venv 就崩，且因 pip 报 already satisfied 极难定位 |
| 把嵌套 venv 的 `No module named 'distutils'` 静默跳过而不申报 | 该失败由**环境搭建方式**造成，属可修项 | 把可修问题伪装成上游缺陷，通过率分母失真（R51），真实修法被埋没 |

## 验证记录

| 项 | 值 |
|---|---|
| 案例 | cffi 2.1.1（C 扩展 + 纯 Python 层） |
| 触发场景 | 构建期 `pip install --target <boot> setuptools` 后把 `<boot>` 放进测试 PYTHONPATH |
| 现象 | `testing/cffi0/test_zintegration.py` **7 项 ERROR**：`No module named 'distutils'` |
| 定位 | 主线「半可见」验证：PYTHONPATH 下 `import setuptools` 成功、`import distutils` 失败；子 venv 里 pip 报 `already satisfied` 却无 setuptools 目录 |
| 修法 | 从测试 PYTHONPATH 移除 setuptools 引导目录，让嵌套 venv 各自真装 |
| 结果 | **7 项 ERROR → 8 passed**（该套件最终计入 `1729 passed, 0 failed`） |

## 关联

- `E512` — 宿主预装 vs CI 干净的依赖缺失（**补依赖**可解；本条补依赖无效，须改供给方式）
- `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` — 子进程覆盖 PYTHONPATH（结论互补）
- `DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable` — 直拷丢失 `.dist-info`（同属「放上去 ≠ 安装」）
