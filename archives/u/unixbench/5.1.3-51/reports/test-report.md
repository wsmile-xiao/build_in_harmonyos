# unixbench 5.1.3-51 测试报告（OHOS PC / aarch64）

> 通过口径（基准类无断言式测试框架）：**每个选中基准项产出有效分数（无 `err`/0 分）且套件退出码为 0**。
> 本报告所有数据来自真机实跑（HarmonyOS PC，HarmonyOS 6.1.0.117，内核 HongMeng Kernel 1.12.0，aarch64）。
> 共享设备：跑分期间其他成员构建任务并行，loadavg 约 20–24；**分数仅供功能验证与相对比较**，不代表设备基准性能。

## 1. 上游测试面与统计

上游 byte-unixbench 5.1.3 的“测试”即 41 个基准项（`UnixBench/Run` 的 testList；
系统 19 / 算术 6 / 非索引 5 / 图形 11）。上游无断言式测试框架，Makefile 的
`check` 目标只做发行完整性与编译检查。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 系统基准 | 19 | dhry2reg、whetstone-double、syscall、pipe、context1、spawn、execl、文件 9 项（fstime/fsbuffer/fsdisk × 聚合/写/读）、shell1/8/16 |
| 算术基准 | 6 | arithoh、short、int、long、float、double |
| 非索引基准 | 5 | C、dc、hanoi、grep、sysexec |
| 图形基准（X11） | 11 | 2D ×10（gfx-x11/x11perf）+ ubgears（上游默认关闭） |
| **合计** | **41** | “通过”= 有效分数 + 退出码 0 |

### 适配后实际执行

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 真机实跑基准项 | 28 | 28/28 有效分数、退出码 0 | 4 次运行去重：index 12 项 + 算术 6 项 + 非索引 3 项 + 文件写/读变体 6 项 + shell16 |
| 平台 SKIP | 13 | 0 执行 | 图形 11（无 X11/x11perf）+ dc（Toybox 无 dc）+ C（Run 硬编码 `gcc`，OHOS 无 gcc），逐项证据见 §3 |
| **鸿蒙特有测试** | **18** | 新增 | `test_package/` 消费者断言（`conan create` 内真实执行）：包结构与 18 个预编译程序、5 项基准实跑（rc=0 + 有效分数 + Index Score）、OHOS 系统信息采集、未知用例负向对照 |
| **合计** | **46** | | |

## 2. 实跑结果（真机证据）

> 原始运行日志与报告副本已按评审意见（规则 19：PR 中禁止 `*.log` 等非标准文件）从提交中移除；
> 关键输出摘录如下，完整日志留存于构建工作区 `reports/`（未提交）。

### index（默认官方 index 12 项，2026-09-27 16:31–16:38，退出码 0）

```
Dhrystone 2 using register variables       28733108.6 lps
Double-Precision Whetstone                     4229.2 MWIPS
Execl Throughput                                 42.2 lps
File Copy 1024/256/4096 bufsize           187239.0 / 51041.0 / 655271.0 KBps
Pipe Throughput                              348447.6 lps
Pipe-based Context Switching                  33392.4 lps
Process Creation                                221.2 lps
Shell Scripts (1 concurrent)                    271.8 lpm
Shell Scripts (8 concurrent)                     81.3 lpm
System Call Overhead                         299236.0 lps
System Benchmarks Index Score                               189.7
```

### 算术 6 项（16:38–16:40，退出码 0；修复后）

```
Arithoh                184890737.2 lps
Arithmetic short/int/long/float/double  189099249.0 / 187195830.7 / 187036923.1 / 186479679.9 / 189861796.9 lps
```

### 非索引 3 项（16:40–16:41，退出码 0）

```
Exec System Call Overhead    30.7 lps
Grep a large file          1521.1 lpm
Hanoi                    236343.2 lps
```

### 文件写/读变体 6 项（16:41–16:48，退出码 0）

```
File Write 1024/256/4096 bufsize   297258.0 / 75435.0 / 1052178.0 KBps
File Read  1024/256/4096 bufsize   650162.0 / 173525.0 / 1690572.0 KBps
```

### shell16（16:48–16:49，退出码 0）

```
Shell Scripts (16 concurrent)    43.1 lpm
```

### 首轮 index 的环境事件（如实记录）

首轮 index 运行在共享设备资源枯竭期（15:03，loadavg 峰值 ~40、内存 30.9G/33.4G 被占），
`tst.sh` fork 失败（`can't fork - try again`）导致套件中止；设备重启恢复后重试一次即通过。
这是共享宿主环境事件，非 unixbench/适配缺陷。

## 3. 平台 SKIP 逐项证据（实测失败输出；原始日志已按规则 19 移除）

| 项 | 实测命令 | 结果 | 原因 |
|----|---------|------|------|
| 2d-rects（图形 10 项同族） | `perl Run -i 1 2d-rects` | rc=1：`Run: "2D graphics: rectangles": sh: pgms/gfx-x11: No such file or directory; aborting` | `gfx-x11` 的 shebang `/usr/bin/perl` 在 OHOS 不存在，且其依赖 `x11perf`/X11 显示（OHOS 无） |
| dc | `perl Run -i 1 dc` | rc=1：`Run: "Dc: sqrt(2) to 99 decimal places": Command "dc" didn't exec; aborting` | Toybox 未提供 `dc` |
| C | `perl Run -i 1 C` | rc=1：`Run: "C Compiler Throughput (gcc)": Command "gcc" didn't exec; aborting` | Run 内 `$cCompiler='gcc'` 硬编码；OHOS 工具链为 clang |
| ubgears | —（上游默认不构建） | 未构建 | 上游 Makefile 默认注释 `GRAPHIC_TESTS`；构建需 X11/GL 头库 |

## 4. 适配缺陷与修复（补丁 0001）

| | 内容 |
|---|---|
| 现象 | 算术族（`Run` 可选 6 项：arithoh/short/int/long/float/double）输出 `COUNT\|0`，Run 以 `Can't take log of 0`（rc=25）中止 |
| 根因 | clang -O2 将 `src/arith.c` 中由 SIGALRM 处理器读取的全局计数器 `iter` 保持在寄存器（纯计算循环内无外部调用），信号处理器读内存恒为 0 |
| 最小矩阵实测 | 3 秒计数：`-O0`=4676336；`-O2`=0；`-O2`+`volatile`=526329615（`int` 变体：0 → 547764980） |
| 修复 | `patches/0001-src-arith.c.patch`：`volatile unsigned long iter;`（不加 `__OHOS__` 守卫；恢复 gcc 构建的逐迭代写内存语义） |
| 复验 | 真机干净重建后算术 6 项全部有效（rc=0；arith 家族 7 个二进制产物同源修复）；`conan create` 消费者测试包含 arithoh 断言防回归 |

## 5. 消费者测试（`test_package/`，18 条断言，conan create 内执行）

- 包结构：`Run`、`Makefile`、`index.base`、18 个预编译基准程序可执行、testdir 数据（5 条）
- 实跑：`perl Run -i 1 dhry2reg arithoh syscall pipe context1` 退出码 0（1 条）
- 报告：生成 + Index Score + 5 项结果行 + Dhrystone/Arithoh 正分数（8 条）
- OHOS 平台签名：`HongMeng Kernel` 系统信息、CPUs 行格式（2 条；实测 `0 CPUs in system`）
- 负向对照：未知用例被拒绝（rc≠0，1 条）
- 运行方式：复制包内 `bin/unixbench` 到可写目录（`cp -a` 保留时间戳），`perl Run ...`

## 6. 复现命令

```sh
# 源码（官方归档端点）与校验
curl -sSL -o ub.tar.gz https://codeload.github.com/kdlucas/byte-unixbench/tar.gz/refs/tags/v5.1.3
sha256sum ub.tar.gz   # 3a6bb00f270a5329682dff20fd2c1ab5332ef046eb54a96a0d7bd371005d31a3

# conan 构建与消费者测试（OHOS 目标）
conan create archives/u/unixbench/5.1.3-51 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
  --build=missing --user=ohpcd --channel=stable

# 真机基准实跑（复制到可写目录后）
cp -a <pkg>/bin/unixbench "$TMPDIR/ub" && cd "$TMPDIR/ub"
perl Run -i 1 index
perl Run -i 1 arithoh short int long float double
perl Run -i 1 hanoi grep sysexec
perl Run -i 1 fs
perl Run -i 1 shell16
```

## 7. 环境与已知平台差异

| 现象 | 根因 | 影响 |
|------|------|------|
| 报告 `System/OS: Toybox` | Toybox `uname -o` 输出 `Toybox` | 报告字段/跨平台可比性 |
| `0 CPUs in system`，不跑 N 副本轮 | OHOS `/proc/cpuinfo` 字段名与 Run 期望不同（`BogoMIPS`/`Features` 大写、无 `model name`；实测 `model name`/`bogomips`/`flags` 命中数均为 0） | 单副本轮；shell8/16 自身并行不受影响 |
| `Language:` 空 + stderr Perl 警告 | 无 `locale` 命令 | 非致命 |
| `3dinfo`/`runlevel`/`who` 缺 | Toybox 未提供 | 报告字段为空；非致命 |
| `./Run` 不可直接执行 | shebang `/usr/bin/perl` 不存在 | 以 `perl Run` 调用 |
| 复制丢时间戳会触发 `make` 用 `CC=gcc` 重建 | `Run` 启动 `make check`；预编译发行需 `cp -a` | README 已说明 |
