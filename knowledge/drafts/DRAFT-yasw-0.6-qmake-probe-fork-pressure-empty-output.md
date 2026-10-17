# DRAFT-yasw-0.6-qmake-probe-fork-pressure-empty-output：`Cannot run target compiler 'clang++'. Output:` 的第二根因 —— 宿主 fork 压力

> Contributor: ohc-worker | Status: Draft | Updated: 2026-09-21
> Source: yasw 0.6 适配（Qt5 + qmake，依赖 `qt/5.15.19.1`）本地 `conan-verify` G2 间歇性失败
> 取证报告：`archives/y/yasw/0.6/reports/yasw-0.6-g2-qmake-probe-finding.md`
> 对应：`knowledge/drafts/DRAFT-yasw-0.6-qmake-probe-fork-pressure-empty-output.kv`

## 现象

qmake 配置阶段报编译探测失败，**Output 段完全为空**：

```console
yasw/0.6@ohpcd/stable: RUN: PATH=".../qt/bin:/data/service/hnp/bin:$PATH" ".../qt/bin/qmake" ".../src/yasw.pro" QMAKE_CC="..." QMAKE_CXX="..."
Project ERROR: Cannot run target compiler 'clang++'. Output:
===================
===================
Maybe you forgot to setup the environment?
```

关键特征：**没有任何** `command not found`、也没有 `Operation not permitted`（签名族）。

## 与 DRAFT-11153 的关系（必须先区分根因）

同一个报错文本有两条互斥的根因链：

| 维度 | DRAFT-11153（PATH 型） | 本条（资源型） |
|---|---|---|
| 根因 | 受限 PATH 不含 `clang++` 所在目录 | PATH 正常，但 `fork()/exec()` 失败 |
| **Output 段** | 可能为空行（shell 未产出） | **必然为空**（子进程从未启动） |
| `command -v clang++` | 失败 | **成功** |
| 同一命令重复执行 | 稳定失败 | **时而通过时而失败** |
| `.qmake.stash` | 通常不生成 / 不完整 | **513 B**（仅 `COMPILER_MACROS`；完整 1440 B） |
| 处方 | 内联 PATH 前缀 | **有限重试**；再改 PATH 无效 |

> 本包曾按 E540（`runner-path-prepend`）的 PATH 处方加前缀 —— **仍失败**；说明不是 PATH 问题。

## 根因

`mkspecs/features/toolchain.prf` 用 `$$system()`（内部 `QProcess`）分两步探测目标编译器：

```makefile
# line 38 (qtVariablesFromGCC)：宏探测
ret = $$system("$$1 -E $$system_quote($$PWD/data/macros.cpp) 2>$$QMAKE_SYSTEM_NULL_DEVICE", lines, ec)
# line 210：include 目录探测（决定 QMAKE_CXX.INCDIRS / LIBDIRS）
output = $$system("$$cmd_prefix $$QMAKE_CXX $$qtMakeExpand($$cxx_flags) -E -v -xc++ - 2>&1 ...", lines, ec)
!equals(ec, 0): qtCompilerError($$QMAKE_CXX, $$output)
```

第一步成功（宏写入 stash），第二步失败。宿主资源实测：

| 指标 | 实测值 | 说明 |
|---|---|---|
| `MemTotal` / `MemAvailable` | 31.1 GiB / 5.1 GiB | 物理 |
| **`Committed_AS`** | **129.3 GiB** | ≈ 物理的 **4.1 倍**（严重超卖） |
| `SwapTotal` 用量 | 50 GiB 中已换出 8.7 GiB | |
| **`/proc/loadavg`** | **38.13 / 30.31 / 28.53**（20 CPU） | 运行队列 ≈ 1.9× CPU 数 |
| 线程数 | 272 | |
| `Max processes` / `Max open files` | unlimited / 32768 | 排除 ulimit |

→ `QProcess::waitForStarted()` 因 `fork()`/`exec()` 失败返回 `false`，`$$system()` 的 `ec != 0`，
而 **stderr 无内容**（子进程从未存在）⇒ Output 段为空。

失败现场 `.qmake.stash` = **513 B**（只含 `QMAKE_CXX.COMPILER_MACROS`），完整应为 **1440 B**
（含 `QMAKE_CXX.INCDIRS` / `LIBDIRS`）—— 这是判断"死在 line 210"的决定性指纹。

## 已排除的假设（逐项实测，全部 ec=0）

| 假设 | 实验 | 结论 |
|---|---|---|
| PATH 缺工具链目录 | `command -v clang++` 在 conan 构建 env 内正常；已加内联前缀 | 排除 |
| `LD_LIBRARY_PATH` 异常 | 3 个变体 | 排除 |
| `TMPDIR` 不可用 | `/tmp` 实测 **Read-only file system**，3 变体（含可写 TMPDIR） | 排除 |
| 调用形式（`cd &&` vs `cwd=`） | 两种形式对照 | 排除 |
| `QMAKE_*=...` 命令行赋值干扰 | 去掉全部赋值 | 排除 |
| 本机 safe-delete 沙箱 | 净化环境重跑 | 排除 |
| 源码目录内容差异 | 复制到副本目录重放 | 排除 |

**冷启动失败率实验**：同命令/同环境/同目录连续 20 次 → **20/20 通过、stash 全为 1440 B**；
而并发/高负载上下文内 6 次中 2 次失败 ⇒ 与调用方式无关，属资源性瞬时失败。

## 推荐方案（已在 yasw 配方落地并验证）

**只对该指纹**做 3 次有限重试，重试前清掉半写 `.qmake.stash`（否则下次会走"从缓存加载"分支
而跳过冷探测）；非该指纹的失败一律原样上抛：

```python
_QMAKE_TRANSIENT_SIGNATURES = (
    "Cannot run target compiler",
    "Maybe you forgot to setup the environment?",
)
_QMAKE_ATTEMPTS, _QMAKE_RETRY_DELAY = 3, 2

for attempt in range(1, _QMAKE_ATTEMPTS + 1):
    if attempt > 1 and os.path.isfile(stash):
        os.remove(stash)                      # 半写 stash → 强制冷探测
    ret = self.run(cmd, cwd=src_dir, ignore_errors=True, stdout=fh, stderr=fh)
    detail = open(log, encoding="utf-8", errors="replace").read()
    if ret == 0:
        return
    if not any(s in detail for s in _QMAKE_TRANSIENT_SIGNATURES):
        break                                 # 非瞬时 → 不重试
    if attempt < _QMAKE_ATTEMPTS:
        time.sleep(_QMAKE_RETRY_DELAY)
raise ConanException(f"Error {ret} while executing\n{cmd}\n完整日志: {log}")
```

复验：`python3 scripts/ohc-run.py conan-verify yasw 0.6` → **G1/G2/G3/G4 全 PASS**。

## 禁止

1. **不要把 qmake 失败一律忽略后继续 `make`** —— Makefile 未生成时 make 会报无关错误，误导定位。
2. **不要沿用"与管道 vs 重定向调用方式有关"的旧结论** —— 本包早期笔记写过该判断，已被上述
   冷启动与变体实验推翻；真实变量是宿主资源。
3. **不要无条件重试** —— 会掩盖真实缺陷（源码错误 / 缺头文件 / spec 不匹配）。
