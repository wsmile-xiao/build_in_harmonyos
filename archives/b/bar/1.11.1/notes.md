# bar 1.11.1 — 适配笔记

## 软件简介

- 项目：clpbar（Command Line Progress Bar）
- 主页：http://clpbar.sourceforge.net/
- 描述：处理数据流并在 stderr 打印进度显示（数据量、吞吐率、剩余时间与进度条）
- 许可证：GPL-2.0-or-later
- 构建系统：autotools（configure 已预生成，含 config.guess/config.sub）

## 依赖结论（r02 静态依赖分析）

- 强制第三方依赖：无（仅 libc：标准头 + posix_memalign/select/strerror/sysconf/sprintf）
- 测试外部命令：tar/dd/cat/rm/cp/echo（标准 coreutils）与 /dev/random、/dev/zero

## 构建要点

- 纯 C 单二进制：`bin_PROGRAMS = bar`（error.c fd.c io.c display.c args.c bar.c）
- 上游测试：`make check` 执行 test-types / test-001 / test-002（test-003/test-004 在 Makefile.am 中注释未启用）
- R15：不得使用 `--build`/`--host` 绕过平台运行期探测；configure 的 `AC_TRY_RUN(sysconf)` 等探测需在真实 OHOS 工具链下执行验证
- configure 探测项：AC_TRY_RUN(sysconf)、页大小、struct iovec、Large File（_FILE_OFFSET_BITS/_LARGE_FILES）

## 门禁状态（r03 本地适配）

- 待补：conan create / conan-verify / finish built / W2 / W3 / W4 证据
---

**编译结束**: 2026-08-20 21:44
**最终状态**: built
