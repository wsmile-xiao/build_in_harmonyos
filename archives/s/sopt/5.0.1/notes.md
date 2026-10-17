# SOPT 5.0.1

源码：官方 v5.0.1 标签，commit `2c2bb53dd8f9da56b5dca23aefec794365649a4a`。
标签内 `SOPT_VERSION=5.0.0` 原样保留。

上游清点：单进程 CPU 配置含 22 个 Catch 入口（55 个 TEST_CASE）、17 个自动示例入口，合计 39 个 CTest 入口；另 3 个 NOTEST 示例照常构建。
全源码共 69 个 TEST_CASE；MPI 5 入口、ONNX 4 入口及 OpenMP 宏保护路径不属于本配置。

配方使用 Eigen 3.4.0、libtiff 4.7.2；上游 Catch3 API 使用 Catch2 3.8.1。
`tests=ON examples=ON dompi=OFF openmp=OFF onnxrt=OFF`，未删上游测试。
按原安装规则先安装 test_data 再测试，避免修改 fixtures 或硬编码数据路径。

本地实际运行环境为 OHOS 7.0.0.32 Beta/API26/AArch64 QEMU。
Conan `os.version=6.0` 仅为依赖匹配元数据；正式 OHOS6、远端 CI、合入及积分均待平台验证。
当前测试执行结果以 reports/test-report.md 与原始日志为准。
---

**编译结束**: 2026-10-04 04:52（完整W3）
**最终状态**: built

本地最终状态：最终W3通过；独立审核、远端CI、正式OHOS6、发布、合入及积分仍待验证。
公开配方已固化标准--debug-find参数；原始wrapper配置与完整W3生成命令、测试注册一致，详见reports/build-report.md。
