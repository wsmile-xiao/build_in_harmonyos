# DRAFT-E640 — uname -s = HarmonyOS：uname 分支型 Makefile 的静默空目标

- **触发**：纯 Makefile 工程，`PLATFORM_OS := $(shell uname | cut -d_ -f1)`，
  ifeq 分支仅 Linux/*BSD/GNU/Darwin/CYGWIN。OHOS 设备 `uname -s` = `HarmonyOS`
  → 全部分支不命中。
- **形态**：共享库/插件目标配方为空，make 报 `Nothing to be done for 'all'`
  后继续编译其余目标，**零报错**；直到下游 `cannot find -l<name>` 才暴露，
  极易误判为源码/依赖问题。实测：pev 0.82（lib/libpe 的 libpe.so 与
  src/plugins 的 5 个输出插件三处全中）。
- **修复**：make **命令行参数** `PLATFORM_OS=Linux`（随 MAKEFLAGS 下传全部子
  make，优先级高于 Makefile 内普通赋值）。**环境前缀无效**：
  `PLATFORM_OS=Linux make` 时，子 Makefile 的 `PLATFORM_OS := $(shell uname…)`
  普通赋值覆盖环境值——这是"传了还不好使"的根因。与 autotools 的
  `--host=aarch64-unknown-linux-ohos` 三元组覆盖同一思想。
- **验收**：确认目标产物真实存在（lib*.so / 插件 .so），不看 make 退出码。
- **实例**：`archives/p/pev/0.82`（conanfile.py build() 传
  `PLATFORM_OS=Linux`，conan create 干净轮通过；notes.md 问题表 #1）。
