# snappy 1.1.7

> 快速压缩/解压库（Google），目标：OpenHarmony PC (aarch64 + CLANG15)

## 基本信息
- 版本：1.1.7
- 上游：https://github.com/google/snappy
- 构建系统：CMake
- 产物：`libsnappy.a`（静态库）、`lib/cmake/Snappy/*.cmake`、`include/snappy*.h`

## 适配要点
- 采用 **Ninja generator** 规避 OHOS hmmac 对 `/bin/sh` 的拒绝（知识库 E346）。
- CMake 4.x 移除 `<3.5` 兼容：snappy `cmake_minimum_required(VERSION 3.1)`，在 conanfile 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（知识库 E103/E187/E447）。
- 关闭 `SNAPPY_BUILD_TESTS=OFF`（仓库惯例，测试依赖可选 GTest/gflags/z/lzo2，避免引入额外依赖体系），功能由 `test_package` 消费者冒烟测试补齐。

## 状态
- `conan create`：✅ PASS（主包 + test_package）
- 测试通过率：`1/1 (100%)`
