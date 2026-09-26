# inotify-info 0.0.4 — OHOS 移植笔记

## 软件简介
inotify-info（mikesart/inotify-info）读取 `/proc/sys/fs/inotify/*` 展示系统 inotify 限额，
并发扫描 `/proc/*/fd` 统计各进程的 inotify watch/instance 占用，再把被 watch 的 inode
映射回文件路径（可理解为 inotify 视角的 lsof）。纯 C++11 + 内置 lfqueue（无锁队列）多线程实现。

- 上游 tag: `v0.0.4`（commit 74beab9cf32147bd6dea8017e0897c7dccd1e5a1）
- 归档 URL: `https://codeload.github.com/mikesart/inotify-info/tar.gz/refs/tags/v0.0.4`
- SHA256: `8a44de6a1750863520954770cfc416ae723ffeb3cc5044ec419fa5392a5d22d1`（独立重算核验）

## License
`MIT AND BSD-2-Clause`：
- 主程序 `inotify-info.cpp`/`inotify-info.h`：MIT（Copyright 2021 Michael Sartain）
- 内置 `lfqueue/`：BSD-2-Clause（Copyright 2018 Taymindis Woon）
两份 LICENSE 均随包归档（`licenses/LICENSE` + `licenses/lfqueue/LICENSE`）。

## 构建策略（零 patch）
上游为纯手写 GNU Makefile，无 configure/CMake，所有关键变量均可在命令行覆盖：

| Make 变量 | 覆盖值 | 原因 |
|---|---|---|
| `INOTIFYINFO_VERSION` | `0.0.4` | 上游默认 `git describe --tags --dirty`，tarball 无 `.git` 会退化为 `unknown`；源码 `#ifndef INOTIFYINFO_VERSION #error` 强制要求该宏 |
| `CC` / `CXX` | OHOS clang / clang++ | 来自 profile `tools.build:compiler_executables` |
| `LIBS` | `-Wl,--no-as-needed -lm -ldl -lpthread -lc++` | 上游写死 `-lstdc++`；实测 OHOS SDK clang 驱动会将其静默改写为 `-lc++ -lc++abi -lunwind`、不替换也能链接成功；按 profile `compiler.libcxx=libc++` 显式选 `-lc++` 仅为保链接行为可追溯（conanfile 内按 settings 动态选择，实测依据见 conanfile.py 注释） |

- `CFLAGS`/`CXXFLAGS`/`LDFLAGS` 不覆盖：上游默认已含 `-std=c++11 -fno-exceptions -fno-rtti -O2` 与告警集，conanbuild.sh 的工具链环境变量经 `+=` 自然合入。
- 不加 `-j`：CI worker 限制 jobserver mkfifo 创建；且仅 2 个翻译单元，串行足够。
- 无需任何源码 patch：源码仅用 `sys/inotify.h`、`getopt_long`、`pthread`、`dirent`、`localeconv` 等 musl 全量提供的接口。

## 运行时验证（OHOS aarch64 真机）
- `inotify-info --version` → 输出 `0.0.4`，退出 0
- 裸跑（无参数，对齐上游 ci.yaml 的 build-with-gcc/zig/docker 冒烟形态）→ 退出 0，
  输出 `INotify Limits:` 与 `max_queued_events`/`max_user_instances`/`max_user_watches` 三项数值
- 裸跑在全零 inode 集合时快速返回（文件路径反查阶段随占用集合规模伸缩）

## 上游测试门禁：NO_UPSTREAM_TESTS
上游**无任何官方测试入口**：
- `Makefile` targets 仅 `all`/`lint`（clang-format）/`clean`/`install`/`uninstall`/release tar 规则，
  无 `test`/`check` target，全文无 `TESTS`/`check_PROGRAMS` 声明
- 无 `tests/` 目录、无 `CMakeLists.txt`、无 `configure`/autotools 文件
- `.github/workflows/ci.yaml` 仅 3 个 job：`lint`（clang-format + git diff --exit-code）、
  `build-with-gcc`、`build-with-zig`（另 `build-with-docker`）；其中"测试"仅为构建后
  `--version` + 裸跑冒烟；`release.yaml` 仅发布草稿

因此按规范记录 `NO_UPSTREAM_TESTS`；上游冒烟形态已由 test_package 的
`run_smoke_tests.sh`（8 项诚实断言）1:1 覆盖并加强：可执行文件存在且可运行、
`--version` 退出 0 且含 `0.0.4`、裸跑退出 0 且输出含 inotify 限额数值。
**不断言 watch/instance 具体计数**——OHOS procfs 不提供 /proc/<pid>/fdinfo（节点级缺失），fdinfo 派生计数结构性不可用，属平台能力边界而非软件自身行为（详见下方「OHOS 平台已知降级」）。

## 已知限制
- debug cfg（`CFG=debug`）上游会追加 `-D_GLIBCXX_DEBUG` 等 GCC libstdc++ 专用宏，本配方固定 release cfg，不受影响
- 文件路径反查需遍历 `--path`（默认 `/`）子树，目录规模大时耗时随被 watch inode 数伸缩，属上游设计行为

## OHOS 平台已知降级（结构性，非环境波动）
- OHOS procfs 不提供 /proc/<pid>/fdinfo（自身进程亦 ENOENT）→ watch 计数与
  被 watch inode→路径反查在本平台结构性不可用；非 SELinux 权限问题，sudo 无解
- 实例检测经 readlink /proc/<pid>/fd → anon_inode:inotify，仅对同 uid 进程有效；
  跨 uid /proc/<pid>/fd 为 Permission denied
- 限额展示（/proc/sys/fs/inotify/*）完全可用；工具经 g_kernel_provides_watches_info
  守卫自动隐藏 watch 统计列
- test_package 因此只断言限额数值与退出码，不断言 fdinfo 派生计数
  （早前“取决于运行环境状态”的表述低估了上述结构性缺失，特此更正）
