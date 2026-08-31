# DRAFT-cpp-taskflow-3.8.0-header-only-cmake-recipe

header-only CMake INTERFACE 库的 Conan 配方模式（OHOS 交叉编译 / Conan 2.29.1 / clang 15）

- **ID**: DRAFT-cpp-taskflow-3.8.0-header-only-cmake-recipe
- **触发工具**: conan | cmake
- **阶段**: packaging | testing
- **严重度**: 🟡 medium (2)
- **分类**: cmake, conan, packaging, headers
- **成对文件**: `DRAFT-cpp-taskflow-3.8.0-header-only-cmake-recipe.kv`（同 stem）

---

## 问题（Problem）

cpp-taskflow 3.8.0 是纯 header-only C++17 库（`add_library(Taskflow INTERFACE)`，仅依赖 C++ 标准库与 pthread），上游 CMake 自带完整 install/export（`TaskflowConfig.cmake` + `Taskflow::Taskflow` target）。但直接 `conan create` 时存在三类隐患：

1. **上游默认开启全量构建**：上游 `TF_BUILD_TESTS=ON` / `TF_BUILD_EXAMPLES=ON` / `TF_BUILD_BENCHMARKS=OFF` 等选项默认，若配方不显式关闭，`conan create` 会连带构建 26 个 unittests 与 examples，引入 3rd-party 测试依赖（doctest/CLI11/spdlog/tbb 等）并严重拖慢配包装插。
2. **package_id 错误粒度**：header-only 库无二进制，若配方按常规 library 声明，会生成与编译器/arch 相关的冗余 package_id，甚至产出空 .so 链接目标。
3. **消费验证缺失**：若不消费上游导出的 `Taskflow::Taskflow` target，test_package 无法证明 `find_package(Taskflow CONFIG)` 可用（R34 实质测试）。

**错误特征**：`TF_BUILD_TESTS` / `TF_BUILD_EXAMPLES`（上游默认开启，配包装插连带构建 unittests）；`conan create ... build_and_test 极慢或失败`；`package_type=library 产生空 lib 目标`；`find_package(Taskflow) 找不到 CONFIG`。

---

## 根因（Root Cause）

header-only INTERFACE target 库没有二进制产物，Conan 配方的「常规库」心智模型（settings→build→package .so/.a）不适用；上游默认开启测试/示例意味着配包装插必须显式反转构建选项，否则把「上游自测」错误地带入「配包装插」门禁。

**影响范围**：header-only C++17/20 CMake INTERFACE target 库（上游自带完整 install/export，如 cpp-taskflow、其他 header-only 任务图/模板/数学库），在 OHOS aarch64 + Conan 2 配包装插场景。

---

## 方案（Solution）

`header-only-cmake-interface-recipe`（conan-recipe-pattern）：

```python
class CppTaskflowConan(ConanFile):
    name = "cpp-taskflow"
    version = "3.8.0"
    package_type = "header-library"        # ① 无二进制
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def package_id(self):
        self.info.clear()                  # ② header-only 与编译器/arch 无关

    def generate(self):
        tc = CMakeToolchain(self)
        # ③ 显式关闭上游默认开启的全量构建选项
        tc.variables["TF_BUILD_TESTS"] = "OFF"
        tc.variables["TF_BUILD_EXAMPLES"] = "OFF"
        tc.variables["TF_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["TF_BUILD_PROFILER"] = "OFF"
        tc.variables["TF_BUILD_CUDA"] = "OFF"
        tc.variables["TF_BUILD_SYCL"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self); cmake.configure(); cmake.build()

    def package(self):
        cmake = CMake(self); cmake.install()   # ④ 走上游 install/export

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Taskflow")
        self.cpp_info.set_property("cmake_target_name", "Taskflow::Taskflow")
        self.cpp_info.libs = []                 # ⑤ 无可链接库
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]
```

- **test_package**：`find_package(Taskflow CONFIG REQUIRED)` + 链接 `Taskflow::Taskflow` + 真实调用 API（创建任务图、定义依赖、run 并断言结果，非打印空壳）。

---

## 验证（Verification）

- `conan create archives/c/cpp-taskflow/3.8.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → exit 0；test_package `1/1` Passed（OHOS aarch64 直接运行，0.02s）。
- 上游 26 个 unittests 全部通过：ctest 发现 2232 用例，逐入口运行 exit 全 0，2232 passed / 0 failed（OHOS 主机直接运行，aarch64-unknown-linux-ohos）。

---

## 适用边界（Scope）

- ✅ 纯 header-only、无二进制、上游自带 `install(EXPORT ...)` + `XConfig.cmake` 的 CMake INTERFACE 库。
- ❌ 需要链接、需要生成配置头、需要消费上游 CMake target 之外逻辑的库（此时应按常规 library 配方，test_package 保留 CMake find_package）。
- ❌ 上游无完整 install/export 时改用 fallback（`header-only-copy-headers`：直接 copy 头目录 + 只设 includedirs）。

---

## 恢复条件（Recovery）

- 配包装插连带构建 unittests/examples → 检查 generate() 是否显式关闭上游 `*_TESTS`/`*_EXAMPLES` 选项。
- 出现空 .so / 编译相关 package_id → 检查 `package_type="header-library"` 与 `self.info.clear()`。
- `find_package(<Name>)` 失败 → 检查 `cmake_file_name`/`cmake_target_name` 与上游导出的 target 名一致。

---

## 查重差异（Dedup）

| 已有条目 | 覆盖点 | 与本文差异 |
|---|---|---|
| E035 | b2/bjam 的 header-only install（Boost） | 构建系统不同（b2 vs CMake INTERFACE）；本文聚焦 Conan 配方形态与上游默认选项反转 |
| E191 | header-only 链接不需要 libc++（`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`） | 本文是配方/packaging 层模式，E191 是 link/测试前置 |
| E307 | test_package 缺 CMake 时直编（不消费 CMake target 的纯头包） | E307 明确「不适用于消费上游 CMake target」；本文正是「消费上游 CONFIG target」的互反场景 |
| E216 | CMakeDeps INTERFACE_INCLUDE_DIRECTORIES（glib/libxml2） | 依赖传递场景，非 header-only 配方主体模式 |

index.tsv 中不存在「header-only CMake INTERFACE + package_type=header-library + 关闭上游默认选项」的完整条目（grep 0 匹配），本 DRAFT 为新增可复用知识，可跨库复用于任何 header-only CMake INTERFACE 库配包装插。