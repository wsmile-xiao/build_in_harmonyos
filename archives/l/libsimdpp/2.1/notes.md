# libsimdpp 2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++ (OHOS SDK)
- 状态: published

## 编译步骤

1. `python3 scripts/ohc-run.py init-build libsimdpp 2.1 --url=https://github.com/p12tic/libsimdpp/archive/refs/tags/v2.1.tar.gz`
2. CMake 配置（Clang，`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）：`cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
3. `make -j2` + `make install DESTDIR=$TEST_PREFIX` —— 纯头文件库，安装头文件与 pkg-config
4. `make check -j1`（上游测试，ctest 4/4 通过）
5. `python3 scripts/ohc-run.py conan-init libsimdpp 2.1` → 改写为 CMake header-library 配方
6. `python3 scripts/ohc-run.py conan-verify libsimdpp 2.1`（G0-G4 全 PASS，ohos-aarch64 profile）
7. `python3 scripts/ohc-run.py finish libsimdpp 2.1 published`（W3 本地 CI 模拟通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 失败：`Compatibility with CMake < 3.5 has been removed` | 上游 CMakeLists 声明 `cmake_minimum_required(2.8)`，CMake 4.1.2 拒绝 <3.5 | 补丁 0001 提升为 3.5；配方 generate() 设置 CMAKE_POLICY_VERSION_MINIMUM |
| 2 | 上游测试在 aarch64+clang15 编译失败：`redefinition of this_compile_arch` | ARM_NEON 与 ARM64_NEON 均通过检测且 define 相同，派发器槽位重复 | 补丁 0002：SimdppMultiarch.cmake 去重（有 ARM_NEON 时不发 ARM64_NEON 槽） |
| 3 | 上游测试编译失败：`argument value 4 is outside the valid range [0, 3]` | clang15 arm_neon.h 对 vextq 立即数严格检查，模板 shift==lane 数实例化越界 | 补丁 0003：align.h NEON/NEON64 分支改为逐值 case（行为不变） |
| 4 | 上游 compile_fail 测试 CMake 版本过低被 CMake 4.x 拒绝 | compile_fail/CMakeLists.txt 声明 2.8.0 | 补丁 0004 提升为 3.5 |
| 5 | 消费者编译失败：`simdpp/detail/preprocessor/stringize.hpp file not found` | 上游 simdpp/CMakeLists GLOB 仅收集 *.h/*.inl，遗漏 46 个 *.hpp | 配方 package() 补充 copy *.hpp |
| 6 | W3 失败：`NotADirectoryError ... predl_cache` | conandata.yml 注释含仓库根 URL，pre-download 正则误提取并子串替换污染 sources URL | 删除注释中的裸 URL（对齐 DRAFT-jwt-cpp/ring-span-lite 知识） |

## 源码修改

patches/（4 个，均由 refresh-patch --auto 生成并登记 conandata.yml）：
- 0001-CMakeLists.txt.patch — cmake_minimum_required 2.8→3.5
- 0002-cmake-SimdppMultiarch.cmake.patch — aarch64 派发槽位去重
- 0003-simdpp-detail-insn-align.h.patch — NEON vextq 立即数兼容
- 0004-test-compile_fail-CMakeLists.txt.patch — compile_fail CMake 版本

## 依赖版本

无第三方运行时依赖（header-only C++11 SIMD 库）；工具链：clang 15.0.4、CMake 4.1.2、Conan 2.29.1。

## 验证结果

- conan-verify: G0-G4 全 PASS（ohos-aarch64 profile，os=OHOS arch=armv8）
- 上游测试: `make check` → ctest 4/4 通过（test_insn/test_dispatcher1/test_expr1/test_compile_fail）
- test_package: `test_libsimdpp` 输出 `OK (11 22 33 44)`，退出码 0
- W3 本地 CI 模拟: build_and_test.sh 100% pass，.ci-result.json 已写入

## 注意事项

- 上游 2.1 已停止维护，CMake 4.x 与 clang15 兼容性是主要适配点，修复均在补丁中体现。
- 依赖 registry 检查（W0/L0i）为库自身（libsimdpp）无依赖，非第三方依赖发布问题。

---

**编译结束**: 2026-09-05 23:47
**最终状态**: published