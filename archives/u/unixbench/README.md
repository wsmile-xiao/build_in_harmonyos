# unixbench（byte-unixbench）

BYTE UNIX Benchmarks（byte-unixbench）5.1.3 —— 经典的 Unix 性能基准套件：由 Perl 驱动脚本
`Run` 编排一组 C 基准程序，覆盖 CPU/算术、进程创建、管道、系统调用、文件 I/O、Shell 脚本等
工作面，并按 `pgms/index.base` 基线对结果做指数归一（Index Score）。

## 功能概述

- **系统基准（19 项）**：Dhrystone 2、Whetstone、System Call Overhead、Pipe Throughput、
  Pipe-based Context Switching、Process Creation、Execl Throughput、File Write/Read/Copy
  （fstime/fsbuffer/fsdisk 三组 × 聚合/写/读）、Shell Scripts 1/8/16
- **算术基准（6 项）**：Arithoh、Arithmetic short/int/long/float/double
- **非索引项（5 项）**：C Compiler Throughput、Dc sqrt、Hanoi、Grep、Exec System Call Overhead
- **图形基准（11 项，X11）**：2D ×10（gfx-x11/x11perf）+ 3D gears（ubgears）——上游默认关闭
- 默认运行 = 官方 index 12 项（单副本与多副本两轮，取决于 CPU 数识别）

## 使用方法（OHOS）

包内 `bin/unixbench` 为完整运行目录（预编译产物）。因为 `Run` 会在运行目录内写
`tmp/`、`results/`，请复制到可写目录执行：

```sh
cp -a <conan包>/bin/unixbench /data/storage/el2/base/cache/unixbench
cd /data/storage/el2/base/cache/unixbench
perl Run                     # 默认 index 12 项
perl Run -i 1 dhry2reg syscall pipe context1   # 快速子集（-i 1 缩减迭代）
perl Run -q index            # 安静模式，报告写入 results/
```

- `Run` 的 shebang 是 `#!/usr/bin/perl -w`，OHOS 无 `/usr/bin/perl`，须用 `perl Run` 调用
  （Makefile 的 `run:` 目标因此不可用）。
- 目录覆盖：`UB_BINDIR` / `UB_TMPDIR` / `UB_RESULTDIR` / `UB_TESTDIR` 环境变量。
- 复制必须保留时间戳（`cp -a`）。若时间戳顺序丢失，`Run` 启动时的 `make check` 会尝试用
  上游缺省的 `CC=gcc` 重建并失败；此时可用 `make CC=clang` 重建（设备有 clang），或按
  `cp -a` 重新复制。

## OHOS 适配要点（aarch64 / HarmonyOS PC）

- **Makefile 零改动**：上游 POSIX Makefile 不改动，构建时以 `make CC=<clang>` 覆盖硬编码的
  `CC=gcc`（编译器取自 Conan `tools.build:compiler_executables`）。
- **1 个 portability 补丁**（`patches/0001-src-arith.c.patch`）：`src/arith.c` 中由 SIGALRM
  处理器读取的全局计数器 `iter` 加 `volatile`。clang -O2 会把该计数器保持在寄存器里（纯计算
  循环内没有外部调用），信号处理器读内存恒为 0 → 算术族基准项（`Run` 可选 6 项：
  arithoh/short/int/long/float/double）全部输出 `COUNT|0`，Run 随即以
  `Can't take log of 0` 中止；`volatile` 恢复逐迭代写内存语义（gcc 构建时的上游行为）。
- **图形项保持关闭**：与上游默认一致（Makefile 中 `GRAPHIC_TESTS` 默认注释掉）；OHOS 无 X11
  头/库与 `x11perf`，模拟器式图形基准不适用。
- 预编译发行：包内直接携带 18 个基准程序产物，消费者无需编译器即可运行。

### 已知平台差异（与 Linux 对比，实测留档）

| 现象 | 根因 | 影响 |
|------|------|------|
| 报告 `System/OS` 显示 `Toybox` | Toybox 的 `uname -o` 输出为 `Toybox`；Linux 为 `GNU/Linux` | 仅报告字段/可比性说明 |
| 报告固定 `0 CPUs in system`，只跑单副本轮 | OHOS `/proc/cpuinfo` 字段名与 Run 期望不同（`BogoMIPS`/`Features` 大小写、无 `model name`），`getCpuInfo()` 解析不到任何字段 → `numCpus=0` | 不执行 N 副本并发轮（shell8/16 自身仍并行）；跨平台比较时需说明 |
| `Language:` 的 charmap/collate 为空 + stderr Perl 警告 | 无 `locale` 命令 | 非致命 |
| `3dinfo`/`runlevel`/`who` 缺失 | Toybox 未提供 | 报告字段为空；非致命 |
| `dc`、`gcc` 缺失 | Toybox 无 dc；OHOS SDK 工具链为 clang | `dc`/`C` 两项跳过 |
| `./Run` 不可直接执行 | shebang `/usr/bin/perl` 不存在 | 用 `perl Run` 调用 |

## 依赖关系

- **运行依赖**：`perl`（核心模块 strict/POSIX/Time::HiRes/IO::Handle）、`sh`、`make`、
  `sort/od/grep/tee/wc`（Toybox 提供）、`sync/cat/pwd`；`shell` 组依赖 `/bin/sh`。
- **构建依赖**：`make` + clang（OHOS SDK）。
- 无第三方库依赖。

## 许可证

上游 GitHub 仓库声明 **GPL-2.0**；v5.1.3 源码包内无独立 LICENSE 文件（归档仅记录来源声明，
不伪造许可证文本）。

## 参考资料

- 上游仓库：https://github.com/kdlucas/byte-unixbench
- 源码与用法：包内 `README`、`USAGE`、`WRITING_TESTS`
- 适配归档：`archives/u/unixbench/5.1.3-51/`（含 `reports/test-report.md` 真机证据）
