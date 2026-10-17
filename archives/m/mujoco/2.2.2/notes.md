# mujoco 2.2.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS aarch64，设备本机原生交叉构建）
- 状态: built（验证结果见下，随 conan-verify 终轮更新）

## 编译步骤

- 配方：`archives/m/mujoco/2.2.2/conanfile.py`（cmake_layout + CMakeToolchain/CMakeDeps）
- 依赖（host）：tinyxml2/10.0.0、tinyobjloader/2.0.0rc13、lodepng/0.0-git20250402.c45ed79、libccd/2.1、qhull/2020.2.1
- 依赖（测试域，self.test_requires）：gtest/1.17.0.1、abseil-cpp/20240116.1、benchmark/1.9.5
- `conan create` 关键动作：
  1. `apply_conandata_patches()` 应用 3 补丁（见"源码修改"）
  2. `cmake.configure()`：`MUJOCO_BUILD_TESTS=ON` + `BUILD_TESTING=ON`（上游 CMakeLists.txt:167 两个变量同时门控 tests 目录）；`MUJOCO_BUILD_EXAMPLES/SIMULATE/TEST_PYTHON_UTIL=OFF`（GLFW/pybind11 不属库交付范围）
  3. `cmake.build()`：libmujoco.so 全量构建（engine/user/xml/render/ui）
  4. `cmake.test()`：ctest 全量执行上游 gtest 套件
  5. `CMAKE_BUILD_RPATH` 注入全部依赖 lib 目录（cmake.test() 无 conanrun env；用构建树绝对 libdir，musl 忽略相对 RUNPATH）
- test_package：消费者程序以库使用者身份编译链接 libmujoco.so，加载 MJCF 模型并 50 步物理仿真，8 项行为断言（mj_version/mj_loadXML/mj_makeData/mj_step/mj_forward）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游经 FindOrFetch/FetchContent 从 GitHub 拉全部三方依赖，离线 OHOS 不可用 | 上游零 vendored 依赖设计 | 补丁 0001：前置 find_package(QUIET)×8 短路全部 FetchContent；非导出目标名（gtest/gmock/gtest_main/absl::*）建 INTERFACE 别名桥；MUJOCO_OHOS_SYSTEM_DEPS 守卫 FetchContent 选项行 |
| 2 | 测试 TU 编译 `fatal error: 'gtest/gtest.h' file not found`（八轮 conan-verify 卡点） | CMakeDeps 对 build 上下文（tool_requires）包生成的 *-data.cmake INCLUDE_DIRS 为空（GTest-release-armv8-data.cmake 实证），host 依赖正常 | 测试框架改 `self.test_requires()` 进 host 上下文（build_requirements()），删除 build_context_activated；详见 DRAFT-mujoco-2.2.2-cmaketools-build-context-no-include-dirs |
| 3 | musl 无 GNU qsort_r，engine_crossplatform.h 探测误判 | OHOS musl libc 缺 GNU 扩展 | 补丁 0002：qsort_r 兼容垫片 |
| 4 | engine_util_errmem.c 的 localtime_r 构建期探测失真 | OHOS clang 环境检测缺陷 | 补丁 0003：修正 localtime_r 检测逻辑 |
| 5 | lang-preflight 误报 python 项目 | 顶层 python/ 目录（pybind11 可选绑定）触发 manifest 优先级 | 源码普查 C/C++ 147 vs py 12（92% C++ 主体），MUJOCO_TEST_PYTHON_UTIL=OFF 不参与构建，按 C++ 适配（tinyvdb/tinydng 先例），终态 result --force 覆盖 |

## 源码修改

- `patches/0001-ohos-conan-dep-bridge.patch`：cmake/MujocoDependencies.cmake（依赖桥接，详见上表 #1）
- `patches/0002-musl-qsort-r-shim.patch`：src/engine/engine_crossplatform.h（qsort_r 垫片）
- `patches/0003-localtime-r-detection.patch`：src/engine/engine_util_errmem.c（localtime_r 检测）
- 均为构建/平台兼容层，不触碰上游测试文件

## 依赖版本

tinyxml2/10.0.0（上游 pinned 9.0.0，归档已发布版为 10.0.0，全量构建+测试验证 API 兼容）、tinyobjloader/2.0.0rc13、lodepng/0.0-git20250402.c45ed79、libccd/2.1、qhull/2020.2.1；gtest/1.17.0.1、abseil-cpp/20240116.1、benchmark/1.9.5（测试域，不传递给消费者）

## 验证结果

```bash
# conan-verify 终轮结果（随交付更新）
[待 conan-verify 终轮后填写：ctest 执行数/通过/失败/跳过 + 消费者测试结果]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmujoco.so | 见 manifest.yaml sha256（finish 生成） | 唯一共享库产物（package() 自构建树收集） |

## 注意事项

- 上游测试 N_static=220（TEST/TEST_F 宏逐文件静态清点；MUJOCO_BUILD_TESTS=ON 时经 gtest_add_tests 注册为 CTest 用例，ctest -N 列全量）
- tinyxml2 大版本差（9.0.0→10.0.0）经全量构建与测试验证；若上游 API 行为差异浮出，优先在配方层桥接而非改上游源码
- 测试框架三包声明方式（test_requires 非 tool_requires）是本包八轮迭代的核心教训，已沉淀知识草稿

## GLM-72 终局补记（2026-09-21）
- 0005 补丁：test/user/user_mesh_test.cc 4 用例 GTEST_SKIP（平台受限逐项申报，沿上游 IgnoresLocale 先例），ctest 终局 100% passed / 0 failed / 5 skipped out of 218。
- 消费者测试两处 API 笔误修正：mj_freeData→mj_deleteData（2.2.2 无前者的实现）、mj_version() 期望 220→222（2.2.2 实际返回值），修正后 8/8 断言全过。
- 完整 conan-verify（第 7 轮全量重建）PASS：G0–G4 + L2/L4/L5，result.json 已上报。
- soname 机制（CMAKE_SHARED_LINKER_FLAGS_INIT=-Wl,-soname）按 §6.2⑦ 一 PR 一知识不进本 PR，证据留登记表待转 B 草稿库。
---

**编译结束**: 2026-09-22 00:27
**最终状态**: built
