# Perl 5.42.2 for HarmonyOS/OpenHarmony

> **编译日期**: 2026-07-26
> **状态**: 已构建
> **构建系统**: Perl Configure + make

## 一、软件简介

Perl 是通用脚本语言和构建期工具，Open MPI、MPICH 以及大量 CPAN/ExtUtils 风格项目会在 configure 或生成阶段调用 perl。本适配将 `perl/5.42.2` 作为 Conan tool package 暴露，安装 `perl`、核心模块和构建期可消费的 `PATH`/`PERL`/`PERL5LIB` 环境。

## 二、编译指导

使用仓库 CI 包入口构建：

```bash
CI_PACKAGES="archives/p/perl/5.42.2" zsh ci/conan/build_and_test.sh
```

配方在 HarmonyOS PC aarch64 真机上使用 Perl `Configure`，禁用当前真机 runtime 不支持或误探测的能力，包括 `IPC/SysV` 与 `prctl(PR_SET_NAME)`，并通过 OHOS 专用 copy-link wrapper 规避 hardlink/symlink 受限问题。

## 三、补丁清单

- `patches/0001-miniperl-touch-noop.patch`: 避免链接 `miniperl` 后执行 `touch`，规避 OHOS 存储对可执行文件时间戳更新的拒绝。
- `patches/0002-extutils-install-write-probe.patch`: `ExtUtils::Install` 在 `-w`/`POSIX::access(W_OK)` 不可信时回退到实际 create/unlink 写入探测。
- `patches/0003-installperl-write-probe.patch`: `installperl` 使用同样的实际写入探测，避免安装目录写权限误判。

## 四、已知限制

完整上游 `make test_harness_notty` 已在真机运行，剩余失败集中在 OHOS 文件系统/POSIX 语义差异，例如 symlink/hardlink、chmod/-w/access、termios/signal、Unix socket 路径长度、locale/timezone，以及直接执行 shell 脚本场景。失败文件已逐项记录在 `5.42.2/upstream-failure-analysis.md`。

## 五、功能验证

- Conan `test_package`: 5/5 PASS，覆盖版本检查、`Config`/`File::Spec` 核心模块加载、`strict`/`warnings` 脚本执行和 Conan build environment 暴露。
- 上游测试：2908 个 test file / 1348696 个 subtest，2864/2908 个 test file PASS，文件级通过率 98.49%。不声明全局 subtest 通过率，因为部分失败文件存在 abort、TAP parse error 或人工终止 hung 子进程。
- PR CI: `archives/p/perl/5.42.2` 已通过 Conan test_package、L0 和 L1。
