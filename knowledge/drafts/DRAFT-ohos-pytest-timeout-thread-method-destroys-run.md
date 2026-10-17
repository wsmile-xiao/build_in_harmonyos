# DRAFT — pytest-timeout 的 `--timeout-method=thread` 会 `os._exit(1)` 杀掉**整个 run**，挂起变得完全不可归因

> 触发事件：werkzeug 3.1.8 适配（PR #11302）CI #54059 —— 全套件超时，
> 日志里**没有用例名、没有失败清单、没有汇总行**（2026-09-21 真机实测）。

## 错误特征

```
werkzeug/3.1.8: upstream pytest: +++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++ (deselected: tests/test_serving.py::test_server[unix socket])
ERROR: werkzeug/3.1.8: Error in build() method
  ConanException: upstream pytest suite failed (R51: ...). Tail:
    File ".../tests/conftest.py", line 115, in __enter__
      self.wait_ready()
    File ".../tests/conftest.py", line 198, in wait_ready
      time.sleep(0.1)
```

鉴别特征：**输出只有 `Timeout` 分隔线 + 超时那一刻的调用栈，零 `FAILED` 行、零汇总行**。

## 根因分析

### 要点 1：无界轮询 + 子进程起不来 = 挂死而非失败

含「以子进程起真实服务」的上游套件，就绪判定普遍写成**无界**循环：

```python
# werkzeug tests/conftest.py:188-198
def wait_ready(self) -> None:
    while True:
        try:
            self.request("/ensure")
            return
        except (ConnectionRefusedError, FileNotFoundError):
            time.sleep(0.1)          # ← 没有退出条件
```

子进程因**任何**原因起不来（缺依赖、缺发行版元数据、worker 资源饥饿 fork 不动），
该用例都不会"失败"，而是**永远挂在那里**。

### 要点 2：收尾方法决定可诊断性 —— 这是本条的核心

| 方法 | 超时后的动作 | 后果 |
|------|-------------|------|
| `--timeout-method=thread` | dump 各线程栈后调 **`os._exit(1)`** | **整个 run 被丢弃**：无用例名、无失败清单、无汇总行，R51 要求的逐项归因一并丢失 |
| `--timeout-method=signal` | SIGALRM 中断**当前用例** | 该用例记为**普通失败**，run 继续，其余用例结果完整保留 |

`thread` 的语义在 pytest-timeout 自己的 docstring 里写得很直白：

```python
# pytest_timeout.py:506-509
"""Dump stack of threads and call os._exit().
...
Then the stacks are dumped and os._exit(1) is called.
"""
```

即：它**不是**"让这个用例失败"，而是"**放弃这次运行**"。对 CI 的直接后果是
——日志看起来很长（有栈可看），但**没有一个可解析的失败项**，配方只能报
"运行器异常退出/未解析到失败用例"，与"pytest 自己崩了"无法区分。

实测对照（同一挂死用例）：

```bash
$ pytest tests/test_hang.py -p timeout --timeout=8 --timeout-method=signal
FAILED tests/test_hang.py::test_hangs - Failed: Timeout (>8.0s) from pytest-timeout.
1 failed, 1 passed in 8.07s          # ← 可归因，run 继续

$ pytest tests/test_hang.py -p timeout --timeout=8 --timeout-method=thread
+++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++
                                     # ← 进程消失，无 FAILED 行
```

## 推荐方案

跑上游套件用 **`--timeout-method=signal`**（仓内先例：`afl-utils 1.35a`）：

```python
cmd = [py, "-m", "pytest", "tests", "-q", "--no-header",
       "-p", "no:cacheprovider", "-p", "timeout",
       "--timeout=120", "--timeout-method=signal",   # ← 不是 thread
       f"--basetemp={basetemp}"]
```

若还要对**纯超时**做有界重试（CI worker 资源饥饿属于基础设施瞬时状态），三条同时满足：

1. 仅当失败**全部**是超时 —— 任何断言失败/收集错误一律直接失败，**不**重跑；
2. 按 **node id 原样重跑**同一批用例 —— 不跳过、不改断言、不删用例；
3. 只重试**一次**，两次输出都写入报告。

```python
timed_out, failed = parse_failures(out)
if timed_out and len(timed_out) == len(failed):     # 全部是超时才重跑
    rc2, out2, _ = run([py, "-m", "pytest", *timed_out, ...])
    if rc2 == 0:
        return                                      # 重跑通过 → 首次超时判定为资源受限
raise ConanException(...)                           # 重跑仍失败 / 非超时失败 → 如实失败
```

## 禁止做法

- ❌ **不要**看到 `Timeout` 分隔线就把该次运行当成"平台问题"重跑：`thread` 的
  `os._exit(1)` 抹掉了全部证据，重跑得到的还是同一份不可归因输出，真实原因
  （缺依赖 / 缺元数据 / 资源饥饿）永远浮不出来。
- ❌ **不要**把"失败全部是超时"以外的失败也纳入重跑：真失败重跑只会重复失败并浪费一轮。
- ❌ **不要**用 `deselect`/`ignore`/`skip` 直接"解决"挂死而不先查清子进程为何起不来：
  挂死是症状，先读 dev-server 子进程日志与 basetemp 现场，再判断是平台限制还是适配缺陷。
  （本次即由此查出真实原因是**子进程起不来**，而非库缺陷。）

## 验证证据

- **主证据**：werkzeug 3.1.8（PR #11302）真机实测。
  - 挂死用例在 `signal` 下产出可解析失败行、run 继续；在 `thread` 下整 run 消失（上表实测）。
  - 换成 `signal` 后完整上游套件仍 **967 passed, 1 skipped, 1 deselected**（无回归）。
  - 定向重跑分支实测：构造「1 个挂死 + 1 个通过」的最小套件，配方真实代码路径发出
    **2 次** pytest 调用（首次全套件 → 按 node id 定向重跑），重跑仍超时后如实抛
    `ConanException`；重跑**只**针对超时的 node id，未重跑通过的用例。
- **交叉佐证**：本仓 `afl-utils 1.35a` 同样使用 `--timeout-method=signal`；
  `DRAFT-ohos-pytest-host-py312-incompat`、`DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv`
  记录了同类"挂起"现象但**未**指出超时方法决定可诊断性。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12.9 / pytest 9.1.1 / pytest-timeout 2.4.0 / conan 2.29.1。

## 查重结论

- 对 `timeout-method` / `timeout_method` 检索全库：**0 命中**。
- 对 `os._exit` 检索：**0 命中**。
- 对 `pytest-timeout` 检索：仅命中若干配方把它作为测试依赖安装的记录，
  无一条讨论**方法选择对可诊断性的影响**。
- 对本仓的"挂起/超时"既有条目检索：
  `DRAFT-ohos-test-subprocess-overrides-pythonpath-needs-venv`（子进程起不来 →
  `wait_ready` 死等）讲的是**为什么会挂**；本条讲的是**挂了之后为什么拿不到证据、
  以及怎样让它变成可归因的失败**——两者互补、不重叠。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。
