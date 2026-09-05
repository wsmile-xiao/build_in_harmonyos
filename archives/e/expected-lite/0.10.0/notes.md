# expected-lite 0.10.0 适配笔记

## 基本信息
- **上游**: https://github.com/nonstd-lite/expected-lite
- **版本**: 0.10.0
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only C++ 库 (CMake INTERFACE library)
- **任务**: 依赖项（第一轮完整适配），executor pc3-22

## 依赖
无任何依赖，仅包含单个头文件 `include/nonstd/expected.hpp`。

## 构建系统
CMake，header-only INTERFACE library。
- `EXPECTED_LITE_OPT_BUILD_TESTS=ON` 启用上游测试
- 上游测试使用 lest 测试框架 (内置于 test/lest/lest.hpp，1483 行)
- clang 15+ (OHOS aarch64) 下 CTest 运行 4 个测试变体: cpp11/cpp14/cpp17/cpp20

## 编译步骤
1. 官方 tarball 下载: https://github.com/nonstd-lite/expected-lite/archive/refs/tags/v0.10.0.tar.gz
   SHA-256: cfe082e4ffedeeedac47763504102646a39c080599c7c1fe99299d6a1f99af92
2. CMake configure:
   cmake -S . -B build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DCMAKE_INSTALL_PREFIX=<prefix> -DEXPECTED_LITE_OPT_BUILD_TESTS=ON \
     -DEXPECTED_LITE_OPT_BUILD_EXAMPLES=OFF
3. cmake --build build -j2 → 4 个测试目标 (cpp11/14/17/20) 构建成功
4. 上游测试: 每变体运行 `All 137 selected tests passed`，全量通过率 137/137=100%
5. cmake --install → include/nonstd/expected.hpp + lib/cmake/expected-lite/*.cmake
6. conan-verify 8 门禁(G0/G1/G2/G3/G4/L2/L4/L5) 全部通过

## 安装路径
- 头文件: `include/nonstd/expected.hpp`
- CMake 配置: `lib/cmake/expected-lite/expected-lite-config.cmake`
- CMake 目标: `nonstd::expected-lite`

## OHOS 适配
- 设置 `CMAKE_SYSTEM_NAME=Linux` 规避 E092 (CMake 不识别 OHOS)；OHOS arch=armv8 映射
  CMAKE_SYSTEM_PROCESSOR=aarch64
- 无需补丁，源码直接编译

## HarmonyOS 专项测试 (test_package)
test_expected_lite_harmonyos.cpp 覆盖：
- aarch64 平台静态断言
- OHOS libc 集成: sysconf(_SC_PAGESIZE)/getuid() 经 nonstd::expected 封装
- value_or 默认值路径 + and_then monadic 链
实测运行: target aarch64: yes / page size 4096 / getuid 正常 / 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 (下载/镜像) | 执行机 github.com:443 不可达 | 使用 codeload/ghfast.top 镜像下载官方 tarball；conan-verify E017 临时镜像注入 |
| 2 | G2 首次下载失败 | ghfast.top 瞬时网络抖动 | 重试 conan-verify 后 G2 通过 |

## 源码修改
无（header-only 库，源码直接编译，零补丁）
---

**编译结束**: 2026-09-02 22:55
**最终状态**: built
