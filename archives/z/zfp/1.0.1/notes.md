# zfp 1.0.1 适配笔记

## 当前状态

已完成 macOS 侧源码核对和 Conan CMake 配方，分支为 `feat/zfp-1.0.1`，版本级与包级 manifest 状态为 `built`（设备验证和 Conan/W3 已通过，尚未 upload）。设备验证运行号、计划哈希和证据目录登记在任务私有审计记录中；W4 输入已在最终验证前的干净 worktree 上生成，CI/Review 仍属于 PR 交付阶段。

## 来源核对

- 上游仓库：[LLNL/zfp](https://github.com/LLNL/zfp)
- 版本：`1.0.1`（GitHub tag，release commit `f40868a`）
- 许可证：BSD-3-Clause（以 release tarball 内 `LICENSE` 为准）
- 源码归档：`https://codeload.github.com/LLNL/zfp/tar.gz/refs/tags/1.0.1`
- 源码归档 SHA-256：`4984db6a55bc919831966dd17ba5e47ca7ac58668f4fd278ebd98cd2200da66f`
- 直接 Conan 依赖：无

## 适配决策

- 使用上游 CMake 构建核心 `zfp` C 库，并保留 `zfp::zfp` CMake 导出目标。
- 默认静态库并启用 `ZFP_ENABLE_PIC`；`shared`/`fPIC` 仍由 Conan options 控制。
- 关闭 OpenMP、CFP、Fortran、Python、utilities 和 examples，避免把额外语言运行时、工具或可执行文件混入核心库包。
- Conan build 阶段保持普通 `BUILD_TESTING` 并运行 `testzfp` 和 `testviews`；关闭 `BUILD_TESTING_FULL`，避免将网络下载的 cmocka/googletest 引入发布配方。设备测试另以 `BUILD_TESTING_FULL=ON` 验证完整上游套件。
- test_package 通过 Conan 生成的 `zfp::zfp` 目标压缩和解压双精度三维数组，逐字节校验可逆 round-trip，并打印实际库版本和压缩大小。

## 补丁

无源码补丁。当前源码的 CMake 安装规则和基础测试入口已覆盖本配方范围；设备端若发现 OHOS 特有编译错误，需以首条真实错误为依据增加最小平台补丁并重新验证。

## 已执行的 macOS 检查

- 官方 tag 归档下载并核对 SHA-256：通过。
- 上游 CMake、安装目标、导出目标、普通测试入口和 LICENSE/NOTICE：静态核对完成。
- `conanfile.py` Python AST 和 `git diff --check`：通过；macOS 未运行 Conan、CMake 构建或 ELF 检查，真实构建和运行证据来自 HarmonyOS 设备。

## 设备验证结果

- 设备环境：Python 3.12.8、Conan 2.29.1、Clang 15.0.4、CMake 4.1.2；10/10 工具检查通过。
- 源码：官方 codeload 归档 SHA-256 `4984db6a55bc919831966dd17ba5e47ca7ac58668f4fd278ebd98cd2200da66f`，单一顶层目录、CMakeLists.txt 和 `include/zfp.h` 检查通过。
- 原生构建：基础配置下 `testzfp`、`testviews` 为 2/2 通过；完整 `BUILD_TESTING_FULL=ON` 配置在 HarmonyOS 设备执行 CTest 186/186 通过、0 失败（91.20 秒）。完整测试使用上游固定 cmocka 1.1.5 的临时兼容处理；其不属于发布包依赖。
- Conan/W3：G0、G1、G2、G3、G4、L2、L4、L5 全部报告 PASS；G2 的干净 `conan create` 重新解包、构建并运行 test_package。G4/L2/L4/L5 原报告因 Conan 2.29.1 包 ID 解析缺陷显示 cache 路径缺失，补充证据 `reports/conan-verify-supplement.md`、`reports/baseline.json` 和 `reports/zfp-package-sha256.txt` 已基于实际 cache 生成：68 个包文件、59 个头文件、1 个静态库、无共享库/ELF；静态包的 NX/PIE/RELRO 不适用。
- 消费者：test_package 真实编译并运行，zfp round-trip 输出 `compressed=288 bytes values=64`，3/3 consumer checks 通过。
- 验证证据：最终分支对应的 `hm-verify` 运行号、计划 SHA-256 和证据目录登记在任务私有审计记录 `task-private/zfp-1.0.1/global-impact-audit.md` 中，运行状态为 `succeeded`。
