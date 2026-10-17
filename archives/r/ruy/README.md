# ruy

Google 的矩阵乘法库。为神经网络推理引擎（最初是 TensorFlow Lite）提供
通用矩阵乘（GEMM）能力：

- **多标量类型组合**：float / double / int8 / uint8 / int16，累加类型可独立指定
  （如 `int8 × int8 → int32`、`uint8 × uint8 → int16`）
- **量化路径**：`MulParams` 支持 `multiplier_fixedpoint` / `multiplier_exponent`
  的逐张量与逐通道定点缩放、zero point 处理
- **后处理融合**：bias 逐列相加、clamp 上下界，可在同一趟内完成
- **快慢双路径**：按平台特化的内联内核（ARM NEON / x86 AVX 系列）与
  纯 C++ 参考实现，两者互为标尺
- **可复用 Context**：`ruy::Context` 承载线程池与 CPU 探测缓存，
  同一实例可反复调用

- 上游：https://github.com/google/ruy
- 构建：CMake（自研 `ruy_cc_library` / `ruy_cc_test` 等规则函数，由
  `cmake/bazel_to_cmake.sh` 生成）
- 依赖：`cpuinfo`（CPU 特性探测）
- 许可证：Apache-2.0
- 测试：上游 33 条 ctest（`ruy/test_fast.cc` 11 条、`ruy/test_slow.cc` 8 条、
  组件单元测试 13 条、溢出专项 1 条、`ruy/profiler` 1 条）

## OHOS 适配

- **必须保留上游测试**：`RUY_MINIMAL_BUILD` 保持顶层默认值 OFF。该变量为真时
  `ruy_cc_test()` 会在第一句 `return()`，33 条测试与 `enable_testing()` 全部消失
  （Conan Center 的配方正是设它为 True，本包刻意不沿用）。
- **vendor googletest**：tarball 中 `third_party/googletest` 是未 checkout 的
  子模块（空目录），上游对它的引用带 `EXISTS` 保护、会静默跳过，导致测试目标
  在链接期找不到 `gtest`。在 `source()` 阶段把 googletest v1.14.0 解压到该路径即可；
  同时 `INSTALL_GTEST=OFF` 防止其产物混进本包，`BUILD_GMOCK=OFF` 省一份编译量。
- **两个补丁**（均非 OHOS 专属）：把 `cmake_minimum_required()` 移到 `project()`
  之前（上游 issue #328）；去掉 `ruy_cc_library` 里 `add_library(... STATIC ...)`
  硬编码的 `STATIC`，使 `BUILD_SHARED_LIBS` 生效。
- **平台名修正**：CMake 不识别 HarmonyOS，`CMAKE_SYSTEM_PROCESSOR` 会变成
  `unknown`、架构分支全部走空。经 toolchain 变量强制 `Linux` / `aarch64`。
- **依赖写法**：裸 ref `cpuinfo/0.0-git20250905.877328f`（不带 `@user/channel`——
  制品仓发布的引用不带 channel，写 `@ohpcd/stable` 会报 `Unable to find in remotes`）。
  平台版 cpuinfo 声明的
  `cmake_target_name` 恰为 `cpuinfo::cpuinfo`，与 ruy 的
  `if (NOT TARGET cpuinfo::cpuinfo)` / `find_package(cpuinfo REQUIRED)` 判据直接对接。
- **包内清理**：移除上游 `install(EXPORT ruyTargets)` 产生的 `lib/cmake/ruy`
  （与 CMakeDeps 生成的 `ruy-config.cmake` 同名碰撞）。
- **产出**：30 个静态库；消费者需显式链接 `m` / `pthread`（已在 `package_info`
  按 `os in ("Linux", "OHOS")` 声明）。
- **无命令行工具**：上游 `ruy_cc_binary` 没有 install 规则，`example` 会被编译但
  不进包，故包内不存在 `bin/`，也不需要 `commands.json`。

## References

- https://github.com/google/ruy
- https://github.com/google/ruy/issues/328（`cmake_minimum_required` 位置问题）
