# DRAFT-ohos-conan-test-package-pythonpath-overwrite-clobbers-runenv — 消费测试脚本赋值 PYTHONPATH 会冲掉 conanrun 注入的依赖路径

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 2 (medium)
> Source: beniget 0.5.0 HarmonyOS PC adaptation（PR 分支 `feat/beniget-0.5.0`），
> 同形缺陷在 meson-python 0.22.0（`feat/meson-python-0.22.0`）实测、在 biopython 1.88（`feat/biopython-1.88`）潜伏
> 对应：`knowledge/drafts/DRAFT-ohos-conan-test-package-pythonpath-overwrite-clobbers-runenv.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv` | 已在 main（draft） | **上游** pytest 套件自己 fork 子进程起服务，`env={**os.environ, "PYTHONPATH": tmp_dir}` 整体覆盖 PYTHONPATH，修法=建独立 venv | 该条全文**不含 `test_package` / `conanrun` 字样**，讲的是「上游套件的子进程」。本条是我方**消费测试**（`test_package/test_*.py`）**赋值**掉了外层 `conanrun` 注入的依赖路径，修法是**追加而非覆盖**（不建 venv）。位置不同、修法不同 |
| `DRAFT-ohos-python-require-no-host-so` | 已在 main（draft） | python-require 包不导出宿主 .so | 与 PYTHONPATH 字符串拼接无关 |
| `DRAFT-pypi-wheel-vendor-python-dep-closure` | 已在 main（draft） | 依赖闭包用 pypi wheel 自带（vendor），绕开 HNP Python 的 site 机制 | 那条是「依赖压根不在图谱里」→ 自带 wheel；本条是「依赖在图谱里、路径也被注入过」→ 只是被我方脚本覆盖掉。本条 `forbid_2` 明确禁止用「删依赖 / 弱化测试」去绕过 |

**全库查证**：对 `test_package` 内层脚本赋值 PYTHONPATH、`conanrun` 注入被覆盖、
`runenv_info` 与 `env_info` 在消费测试中的差异，在 `knowledge/graph/`、`knowledge/doc/`、
`knowledge/drafts/` 中 grep —— 未命中同名方法论条目。

## Scope（何时用）

本仓 Python 包适配，且**消费测试是两层构造**时：

```
test_package/conanfile.py          ← 外层：self.run(..., env="conanrun")
test_package/test_<pkg>.py         ← 内层：再起一个解释器跑真实断言
```

命中信号（任一即应排查）：

| 信号 | 检查命令 |
|---|---|
| 内层脚本赋值 PYTHONPATH | `grep -n 'env\["PYTHONPATH"\] *=' archives/<pkg>/*/test_package/test_*.py` |
| CI 报依赖缺失，但依赖已在 `requirements()` | 日志 `ModuleNotFoundError: No module named '<dep>'` |
| CI 日志出现 `deprecated: 'env_info' used in: <dep>` | 说明该依赖的路径**根本没进** conanrun（见下文「两个缺陷常同时出现」） |

## ⭐ 核心结论：**赋值**与**追加**的差别，就是「依赖找不到」与「一切正常」的差别

本仓 Python 包的消费测试典型写法（内层脚本）：

```python
site = os.path.join(pkg, "lib", "python3.12", "site-packages")
env = dict(os.environ)
env["PYTHONPATH"] = site              # ← 赋值：把 conanrun 注入的一切冲掉
subprocess.run([py, "-c", SMOKE_PY], env=env)
```

`conanrun` 已经把被测包**运行期依赖**的 site-packages 挂进了 PYTHONPATH
（由主配方的 `runenv_info.append_path("PYTHONPATH", ...)` 决定）。上面这行**赋值**
把它整体替换成只有被测包自己的目录，于是内层进程 import 依赖时：

```console
FAIL: beniget API: Traceback (most recent call last):
  File "<string>", line 8, in <module>
ModuleNotFoundError: No module named 'gast'
```

**正解——追加而非覆盖**：

```python
env["PYTHONPATH"] = os.pathsep.join(
    [site] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
```

> 判据：内层脚本要做的是「**把被测包也放到路径上**」，不是「**定义路径是什么**」。
> 后者是外层 `conanrun` 的职责。这与同仓 smoke 脚本对 `sys.path` 的处理
> （`sys.path[0:0] = [...]`）是同一思路。

## ★ 为什么这个 bug 特别难发现

两个方向的不对称，使任何「只看一个文件」的排查都得出错误结论：

| 视角 | 看到的 |
|---|---|
| 看主配方 `conanfile.py` | `runenv_info.append_path("PYTHONPATH", ...)` —— **正确**，依赖路径确实注入了 |
| 看内层脚本 `test_*.py` | `env["PYTHONPATH"] = site` —— 看起来也**合理**（「让被测包可导入」） |
| 合起来 | 外层注入的路径被内层**销毁**；报错指向依赖缺失，而依赖声明、构建、图谱全都没问题 |

因此报错信息（`No module named '<dep>'`）会把作者引向 `requirements()`——**修那里没有用**。

## ★★ 两个缺陷常同时出现，必须按顺序排查

内层赋值是**其中一半**；另一半是依赖的路径**压根没进 conanrun**：

```console
WARN: deprecated: Usage of deprecated Conan 1.X features that will be removed in Conan 2.X:
WARN: deprecated:     'env_info' used in: packaging/26.3, pyproject-metadata/0.12.1
```

`env_info` 是 Conan 1.x 的接口，在 Conan 2 上**只告警、不生效**——所以这类依赖的
site-packages 从未出现在 `conanrun` 里。此时：

- 若只修「赋值→追加」：**仍然失败**（继承到的 PYTHONPATH 里本来就没有该依赖）；
- 若只在外层显式注入、内层仍赋值：**仍然失败**（注入又被冲掉）。

诊断顺序：

```
1. 依赖路径在被继承的 PYTHONPATH 上吗？
   ├─ 在  → 是「赋值覆盖」缺陷（本条主结论）      → 改追加
   └─ 不在 → 是「env_info 失效 / 未传播」缺陷      → 外层用 runenv_info 或显式注入依赖
                                                   site-packages，并仍按追加方式合并
2. 两者都命中时 → 两处都改（meson-python 即此情形）
```

## 实测记录

| 包 | CI | 报错 | 判定 |
|---|---|---|---|
| beniget 0.5.0 | #65761 | `ModuleNotFoundError: No module named 'gast'` | **纯赋值覆盖**：gast 已在 `requirements()`，其 site-packages 也确在 conanrun 的 PYTHONPATH 上；唯一原因就是 `test_beniget.py:88` 的 `env["PYTHONPATH"] = site` |
| meson-python 0.22.0 | #65762 | `ModuleNotFoundError: No module named 'pyproject_metadata'` | **两个缺陷同时命中**：`packaging`/`pyproject-metadata` 用 `env_info`（conanrun 空）+ 内层脚本赋值覆盖 |
| biopython 1.88 | （潜伏） | 同形：`import numpy as np` 而 numpy 路径来自内层 | 同族，已按本条修正 |

## 反例（禁止）

- ❌ 把依赖从 `requirements()` 删掉、或删掉消费测试里的 import/断言去「消除」报错——
  依赖是真实的运行期需求（beniget 要 gast 建 AST、meson-python 要 pyproject-metadata
  解析元数据），删掉等于让消费测试不再证明包可用（R51/R34 口径）。
- ❌ 只在本地「碰巧通过」就收工——宿主解释器若恰好装了同名包，赋值覆盖也会「通过」，
  这是假绿，CI 必挂。判定必须看**被继承的 PYTHONPATH 是否含依赖路径**。
