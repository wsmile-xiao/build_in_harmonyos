# gperftools

gperftools 是一组高性能 C++ 内存分配与性能分析库，其中 `tcmalloc` 提供可替代系统 `malloc` 的分配器。

## 功能概述

- 提供 `tcmalloc_minimal`、可选的完整 tcmalloc、CPU profiler 和调试分配器。
- 暴露 `tc_malloc`、`tc_free`、`tc_malloc_size` 等 C API，便于 C/C++ 消费者集成。
- 上游使用 Autotools 构建，并自带完整 `make check` 测试套件。

## OHOS 适配

- 面向 HarmonyOS PC aarch64/OHOS 目标，补充 release tarball 的 `config.guess` 识别。
- 修复生成的 `configure` 在 HMDFS 上创建私有临时目录时的 `umask 077` 问题。
- 默认构建静态 `tcmalloc_minimal`，避免引入未验证的可选栈展开依赖；完整 profiler/heap 功能通过 Conan options 开启。
- 设备侧必须以真实 `make check` 和 Conan `test_package` 结果确认平台行为。

## 依赖关系

- 默认构建无 Conan 依赖。
- 开启 `enable_libunwind=True` 且构建完整栈跟踪功能时使用 `libunwind/1.6.2`。

## 参考资料

- 官网与源码仓库：<https://github.com/gperftools/gperftools>
- 版本目录：[`2.17.2`](2.17.2/)
