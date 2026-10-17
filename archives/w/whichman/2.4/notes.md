# whichman 2.4 适配笔记

## 源码与依赖

- 源码：Debian 官方归档保存的未重打包上游 `whichman_2.4.orig.tar.gz`。
- 构建系统：纯 Makefile；无 `configure` 步骤。
- 依赖：无第三方依赖，仅使用 POSIX libc。
- 上游测试审计：源码没有 `test/` 或 `tests/` 目录，Makefile 也没有 `check` 或 `test` 目标，因此上游自动化测试为 0/0（N/A）。

## HarmonyOS 适配

上游 Makefile 默认指定 `CC=gcc`。配方从 Conan profile 的
`tools.build:compiler_executables` 获取 C 编译器，并执行：

```bash
make -j1 CC='<OHOS clang>'
```

命令行变量会覆盖上游默认值，无需修改源码或引入补丁。手工编译已生成
`whichman`、`ftff` 和 `ftwhich` 三个 AArch64 OHOS PIE ELF。

## 验证范围

`test_package/test.sh` 在 AArch64 运行器上验证：

1. 三个打包命令均存在且可执行；
2. `whichman -e` 使用 `MANPATH` 精确定位 man page，并确认不存在条目返回失败；
3. `ftwhich -0` 在隔离的 `PATH` 中定位可执行文件；
4. `ftff -0` 在临时目录树中定位文件。

配方以 `-static` 链接三个命令行工具。AArch64 HarmonyOS runner 直接执行
功能断言；x86 runner 必须通过 `qemu-aarch64` 执行同一静态 AArch64 二进制，
没有 QEMU 时测试会失败而不是成功跳过。本地 qemu-aarch64 已完整执行
`test_package/test.sh` 的 7 个断言，结果全部通过。

## 对话记录

### 对话 #1 — 2026-09-20

- 依赖预检确认无第三方 Conan 依赖；语言预检确认主体为 C。
- 使用 OHOS clang 成功构建三个动态 PIE AArch64 ELF；Conan `conan create`、
  G1–G4 和 W3 本地 CI 均通过。
- 未遇到新的通用编译错误，因此不新增知识草稿。
---

**编译结束**: 2026-09-20 07:42
**最终状态**: built
