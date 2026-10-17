# DRAFT-ohos-harmonyos-compat-os-popen-double-wrap — 平台 compat 层 os.popen 二次 TextIOWrapper 包装致 read() 必崩

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-18 | Severity: 🔴 blocking
> Source: PR #10408（greenlet 3.5.6 上游测试 test_version 失败）——根因定位到 python/3.12.9 补丁 0014

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E226 | 已收录 | **消费者侧**报错与绕过：`TypeError: can't concat str to bytes` 时，「用自己的 subprocess 字节捕获替代 os.popen，再显式 decode 一次」（方法名 `capture-subprocess-bytes-explicitly`） | 本 skill 是**平台侧根因与根治**：缺陷在平台 compat 层 `_harmonyos_compat.py` 把 `os.popen` 包装成 subprocess 时**既传 `text=True` 又对 `proc.stdout` 二次套 `io.TextIOWrapper`**，导致 `read()` 必崩。E226 让每个消费者各自绕行（N 个包各写一遍），本 skill 给出**一处修正、全平台受益**的改法（`return proc.stdout`），并指明可复现的最小判据 |
| DRAFT-cadical-2.1.3-ohos-popen-pipe-lifetime | draft | 管道生命周期（读者先退出 → 写者 SIGPIPE） | 问题层不同：本条是**解码层**（双重 TextIOWrapper），与管道生命周期/信号无关 |
| DRAFT-itsy_bitsy-0.8-upstream-test-materialization | draft | 上游测试物化（该草稿中亦出现过同报文，属消费侧遭遇记录） | 本 skill 不讨论测试物化，只定位平台 compat 层缺陷本身 |

**撞车判定**：全库查证 `TextIOWrapper`（0 命中）、`_harmonyos_compat`（0 命中）、`_wrapped_os_popen`（0 命中）、`双重包装`（0 命中）。E226 收录的是**消费者如何绕过**，未记录**平台 compat 层自身的包装缺陷**与根治改法，故作为 E226 的根因补全条目申报（问题层 = 平台运行时，增量 = 根因定位 + 一处修正）。

## Scope（何时用）

- 在 `python/3.12.9` 运行时下，任何调用 `os.popen(...).read()` / `os.popen(...)` 迭代取输出的场景
- 上游测试用 `os.popen` 跑子进程并读结果（尤其「拿不到输出即断言失败」的用例）
- 现象：套件里某个用例稳定报 `TypeError: can't concat str to bytes`，且**换成纯 subprocess 就正常**

## Symptom

```python
>>> import os
>>> os.popen("echo hi").read()
TypeError: can't concat str to bytes
```

traceback 落点在解码层，极具误导性：

```
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<frozen codecs>", line 321, in decode
TypeError: can't concat str to bytes
```

真实案例（greenlet 3.5.6 上游 `tests/test_version.py:36`）：

```
upstream pytest: 1 failed, 161 passed, 10 skipped, 171 warnings
FAILED src/greenlet/tests/test_version.py::VersionTests::test_version
```

> 注意上游语义：该用例对「拿不到版本串」是 `skipTest`，但**对异常不是**——所以
> 平台缺陷把它从 skip 变成硬 failure，套件永远到不了 100%。

## Root Cause

仓库 `python/3.12.9` 的补丁 `0014-Lib-_harmonyos_compat.py-HarmonyOS-subprocess-compat.patch`
生成 `Lib/_harmonyos_compat.py`，为绕过 SELinux 域限制下 fork+exec 不可用，把
`os.system` / `os.popen` 改写为 subprocess 实现。其中 `os.popen` 包装写成：

```python
# _harmonyos_compat.py:101-105（修复前）
proc = subprocess.Popen(command, shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True)          # ← text=True：proc.stdout 已是文本流
return _io.TextIOWrapper(proc.stdout)       # ← 再包一层 → 双重解码
```

`text=True` 让 `proc.stdout` **已经是 `io.TextIOWrapper`**；再套一层就形成双重解码，
`read()` 时内层已返回 `str`，外层仍走 codecs 的字节路径，于是
`TypeError: can't concat str to bytes`。

**判据（三条独立验证，均不含任何三方库）**：

| 验证 | 结果 |
|------|------|
| `os.popen('echo hi').read()`（受影响运行时） | ✗ `TypeError: can't concat str to bytes` |
| 只复刻「`text=True` + 二次 `TextIOWrapper`」 | ✗ 同样 TypeError |
| 去掉二次包装（`return p.stdout`） | ✓ 正常返回 |

**易混点**：3.9.x 的同类 compat 补丁（`3.9.25/0003`、`3.9.0/0009`）**只包装
`os.system`、不碰 `os.popen`**，所以本缺陷是 **3.12.9 独有**，不要套用到 3.9 系。

## Workaround / 修复

- **根治（推荐，一处改全平台受益）**：改 `patches/0014-...patch`，把
  `return _io.TextIOWrapper(proc.stdout)` 换成 `return proc.stdout`，并删掉不再使用的
  `import io as _io`（同时把 hunk 计数同步更新）。本草稿出处 PR 即此改法，实测从补丁
  提取生成的新文件后，`os.popen('echo hi')` 返回 `'hi\n'`。
- **消费侧绕行（E226 的做法）**：在配方里自建 subprocess 字节捕获替代 `os.popen`，
  再显式 decode 一次。可行，但每个包都要各写一遍，且掩盖了平台缺陷。
- **不改上游测试**：若只是想让套件跑通，可在 pytest 前经 `PYTHONPATH` 注入
  `sitecustomize.py` 就地纠正 `os.popen`（greenlet PR #10408 采用的过渡方案）。

## Prevention

- 平台 compat 层改动后，用最小式
  `python3 -c "import os; os.popen('echo hi').read()"` 做冒烟（一行即可暴露本类缺陷）。
- 审查 compat 层代码时重点看「`text=True`/`encoding=` 与再包装」的组合——两者只要同时
  出现就是双重解码。
- 判定「平台缺陷 vs 移植缺陷」时，用最小式在**宿主 python** 上复现即可分离（不涉及被
  适配的库）。

## References

- PR #10408（greenlet 3.5.6，消费侧遭遇与过渡绕行）
- E226（消费者侧 workaround：capture-subprocess-bytes-explicitly）
- `python/3.12.9/patches/0014-Lib-_harmonyos_compat.py-HarmonyOS-subprocess-compat.patch`
