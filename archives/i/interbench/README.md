# interbench

## 是什么

interbench 是 Con Kolivas 编写的内核交互性基准工具：通过组合多种模拟负载
（Audio / Video / X / Gaming / Burn / Write / Read / Compile …）测量调度
延迟与抖动，用于对比不同内核配置与负载组合下的交互性表现。

## 功能概述

- 单一可执行文件 `interbench`；`-h` 输出全部选项
- 基准选择：`-W <bench>` 添加基准负载、`-X` 排除；`-w <load>` / `-x <load>`
  添加 / 排除被测试的背景负载
- 运行控制：`-t <秒>`（默认 30）、`-l <loops>`（每毫秒循环数，默认复用已存
  校准值）、`-b` 强制重校准、`-c` 仅控制台输出（默认同时写日志文件）、
  `-r` 以实时调度方式跑基准
- 校准结果持久化：`interbench.loops_per_ms`（首次运行生成，之后运行复用）

## OHOS 适配

- 交叉编译目标 `aarch64-linux-ohos`，`package_type = "application"`；
  官方 Makefile 直接构建（`make CC=clang`），产物安装到 `bin/interbench`
- 补丁 0001：显式 `#include <sys/stat.h>`——clang 15 + musl 下 `struct stat`
  不再经其他头文件传递包含
- 补丁 0002：Makefile 先决条件行中的 `-lm` 移除——GNU make 会把不认识的
  先决条件当作文件目标（报 `No rule to make target '-lm'`）；`-lm` 仍经
  LDFLAGS 参与链接
- 首次运行要求当前目录内 `interbench.read` 大小恰为 `MemTotal×1024` 字节，
  否则会实写一份等大文件（真机为 32GB 级）；消费者测试以稀疏文件满足
  尺寸校验（详见版本级 `notes.md`）
- 非 root 运行时 `SCHED_FIFO` 不可用，工具提示 "Results will be unreliable"
  后继续运行（退出码 0）

## 依赖关系

无外部编译依赖：产物 ELF 动态段仅 NEEDED `libc.so`（OHOS 统一 libc，
`libm` / `librt` / `libpthread` 为其内建部分）。

## 参考资料

- 上游仓库：https://github.com/ckolivas/interbench
- 版本归档：https://github.com/ckolivas/interbench/archive/refs/tags/v0.31.tar.gz
