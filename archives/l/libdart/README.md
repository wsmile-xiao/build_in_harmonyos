# libdart

## 简介

libdart（Dart）是 Target 开源的高性能、网络优化的二进制 JSON 协议库，提供：
- **header-only C++14 接口**（`dart::packet` / `dart::buffer` / `dart::heap`）用于日常使用
- **ABI 稳定的 C89 绑定层**（`src/heap.cc`、`src/buffer.cc`、`src/generic.cc`，`-Dbuild_abi=ON` 时构建）
- 对象键查找对数复杂度、迭代顺序稳定、读路径零接收端分配

上游仓库（github.com/target/libdart）已于 2024-07 归档，v1.4.0 为最终稳定版本。

## OHOS 适配

- Header-only 库：配方 `package_type=header-library`，仅安装 `include/dart.h` + `include/dart/`（.h/.tcc）
- 公开头文件依赖 Microsoft GSL（`gsl::span`）→ `requires("ms-gsl/4.2.1")`
- 上游 CMake 用 `find_path/find_library` 探测依赖，配方 generate() 双路注入：
  - `CMAKE_INCLUDE_PATH` / `CMAKE_LIBRARY_PATH` 供 find_* 探测
  - `CMAKE_CXX_FLAGS -I` 供被 `#include` 的头文件（如 yaml.h）编译
- CMakeToolchain 无 `cxxflags` 属性（AttributeError），编译器标志一律经 `tc.variables["CMAKE_CXX_FLAGS"]` 注入
- CMake >= 4 拒绝 `cmake_minimum_required(3.1.0)`，注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- codeload URL 末段无扩展名，conandata.yml 显式 `filename` 才能被 conan get() 正确解压

## 依赖

| 包 | 用途 |
|----|------|
| ms-gsl/4.2.1 | requires（公开头文件依赖 gsl::span） |
| rapidjson/1.1.0 | test_requires（DART_HAS_RAPIDJSON：json_test / parse / to_json） |
| libyaml/0.2.5 | test_requires（yaml_test） |

## 功能验证

- 上游测试：unit_tests 170 + json_test 2 + yaml_test 1 + abi_tests 70 = **243** TEST_CASE/SCENARIO，`ctest` 4/4 通过（build() 内全量运行）
- 消费者测试（test_package/test.cpp）：parse → 公开 view 取值 → make_object → to_json 往返，PASS
- 鸿蒙专项测试（test_package/test_ohos.cpp）：char 符号探针、int64/double 精度、1MB 大对象、深层嵌套往返，PASS
- conan-verify G0-G4 + L2/L4/L5 全部通过；finish published（W3 本地 CI 模拟通过）

## 知识沉淀

- 本轮新增草稿：`knowledge/drafts/DRAFT-libdart-cmake-toolchain-find-deps-injection.kv/.md`（路径 B 知识库扩展）
- 复用的既有知识：E276/E392/E483（codeload filename）、DRAFT-E321（CMAKE_POLICY_VERSION_MINIMUM）