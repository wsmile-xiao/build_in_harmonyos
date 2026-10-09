# rmw 0.9.5 - HarmonyOS 编译记录

## 概述

rmw（ReMove to Waste）是命令行回收站工具，支持将文件安全移入遵循 FreeDesktop
Trash 规范的回收站目录，并可按过期策略清理、用 `-z` 恢复。

**编译状态**: ✅ 成功（conan create rc=0，test_package 消费者用例 11/11 断言通过）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC / OpenHarmony aarch64 |
| C 库 | musl libc |
| 构建系统 | meson（工具包 meson/1.11.0） |
| 依赖 | canfigger/0.3.2、ncurses/6.6（均为 conan 包）+ vendored musl-fts 1.2.7 |

## OHOS 适配要点

1. **canfigger**：meson `dependency('canfigger')` 依赖 pkg-config 与 wrap-git 网络
   fallback，OHOS 上均不可用 → 补丁改为 `cc.find_library('canfigger', has_headers:)`，
   由配方注入依赖包的 `-I`/`-L`。
2. **curses/menu**：OHOS ncurses 包只导出 `ncursesw.pc`（prefix=/），且 include 为扁平
   布局、纯静态库 → 补丁改为 `cc.find_library('ncursesw'/'menuw', has_headers:)`。
3. **fts(3)**：musl 无 fts，上游 `src/bsdutils/rm.c` 硬依赖 → vendored musl-fts 1.2.7
   （NetBSD 实现，BSD-3-Clause）编入 bsdutilsrm 静态库，另生成最小 config.h
   （`HAVE_DIRFD=1`）。
4. **NLS**：musl 无 libintl → `-Dnls=false`，上游 gettext.h 自带 stub，零额外补丁。
5. **btrfs 克隆**：`host_machine.system()` 在 OHOS 返回非 `linux`，自动不启用。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.9.5 | built | 2026-09-29 |
