# inotify-info — OpenHarmony 编译档案

## 软件简介
inotify-info（mikesart/inotify-info）是一个命令行工具：读取 `/proc/sys/fs/inotify/*`
展示系统 inotify 限额，并发扫描 `/proc/*/fd` 统计各进程的 inotify watch/instance 占用，
再把被 watch 的 inode 反查映射回文件路径——可理解为 inotify 视角的 lsof。

## 功能概述
- `inotify-info` — 打印 inotify 限额 + 按进程的 watch/instance 统计 + 被 watch 文件路径
- `-s|--short-stat` — 快速总览：仅限额与总量（跳过路径反查）
- `-p=PATH|--path=PATH` — 指定路径反查搜索根（默认 `/`）
- `--sort-by-instances` — 按实例数排序；`--threads=##` 并发线程数
- `--ignoredir=NAME` — 反查时忽略目录名；`-v` 详细输出；`--no-color` 去色
- `--version` / `-h` — 版本与帮助

## OHOS 适配要点
- **零 patch**：上游为纯手写 GNU Makefile，`CC`/`CXX`/`CFLAGS`/`CXXFLAGS`/`LDFLAGS`/`LIBS`/
  `INOTIFYINFO_VERSION` 全部可命令行覆盖，OHOS clang 直接交叉编译
- **版本串**：tarball 无 `.git`，上游默认 `git describe` 兜底 `unknown` → 构建时显式传
  `INOTIFYINFO_VERSION=0.0.4`（源码 `#error` 强制要求该宏有值）
- **C++ 运行库**：上游 `LIBS` 写死 `-lstdc++`；实测 OHOS SDK 26.0.0.18 clang 15.0.4
  驱动会将其静默改写为 `-lc++ -lc++abi -lunwind`（不替换也能链接成功），按 profile
  `compiler.libcxx=libc++` 显式选 `-lc++` 仅为保链接行为可追溯
- **平台能力**：OHOS 内核提供完整 inotify（`sys/inotify.h` + `/proc/sys/fs/inotify/*`），
  源码仅依赖 musl 全量提供的 `getopt_long`/`pthread`/`dirent`/`localeconv` 等接口
- **双许可**：主程序 MIT（Michael Sartain）+ 内置 lfqueue BSD-2-Clause（Taymindis Woon）
  → `MIT AND BSD-2-Clause`，两份 LICENSE 均随包归档

## 依赖关系
- 无外部依赖（仅 libc/libm/libdl/libpthread + libc++）

## 测试
- 上游：无任何 test/check 入口（Makefile 无 test target、无 tests/ 目录、无
  CMakeLists/configure；workflows 仅 lint + 构建冒烟）→ 按规范记录 `NO_UPSTREAM_TESTS`
- test_package：上游冒烟形态（构建后 `--version` + 裸跑）1:1 覆盖并加强为
  `run_smoke_tests.sh` 8 项诚实断言：可执行文件存在且可运行、`--version` 退出 0
  且含 `0.0.4`、裸跑退出 0 且输出含 inotify 限额数值。
  **不断言 watch/instance 计数**（OHOS procfs 不提供 /proc/<pid>/fdinfo，fdinfo 派生
  计数节点级缺失、结构性不可用，属平台能力边界而非软件行为，详见 0.0.4/notes.md 降级说明）

## 参考资料
- [inotify-info GitHub](https://github.com/mikesart/inotify-info)
- [inotify(7) man page](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [lfqueue](https://github.com/Taymindis/lfqueue)
