- **三方库名称**：CLI11
- **上游版本**：v2.6.2
- **上游仓库地址**：https://github.com/CLIUtils/CLI11
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 22 | 来源：上游 `tests/` 目录，使用 CMake/CTest + Catch2 v2.13.10，覆盖命令行解析、选项、子命令、配置文件、验证器及编码等功能 |
| 集成测试 | 1 | 来源：上游 `tests/link_test_2.cpp`，验证 CLI11 多翻译单元链接 |
| 其他测试 | 1 | 来源：上游 `tests/TimerTest.cpp`，验证计时器功能 |
| **合计** | **24** | 当前 Linux/OHOS、C++11、Boost 关闭配置下生成的完整 CTest 测试集 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 22 | 不变 | 在主配方 `build()` 阶段通过 `cmake.test()` 完整执行 |
| 集成测试 | 1 | 不变 | 执行上游多翻译单元链接测试 `link_test_2` |
| 其他测试 | 1 | 不变 | 执行上游计时器测试 `TimerTest` |
| 鸿蒙特有测试 | 4 | +4 | `test_package/test.cpp` 提供消费者视角测试断言，验证 `CLI::App` 实例化、选项添加、命令行解析及解析结果 |
| **合计** | **28** | **+4** | 24 个上游 CTest 测试程序和 4 个新增消费者测试断言全部通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 修改均通过补丁应用，未删除测试、未修改断言或测试逻辑。主配方启用 `BUILD_TESTING=ON` 和 `CLI11_BUILD_TESTS=ON`，在构建完成后调用 `cmake.test()` 执行完整测试集。

1. **修改的测试文件**：`tests/CMakeLists.txt` 与 `tests/catch.hpp`（通过 `patches/0001-use-local-catch2.patch` 应用）
   - **修改原因**：上游 `tests/CMakeLists.txt` 用 `file(DOWNLOAD ...)` 从 `github.com/philsquared/Catch` 拉 Catch2 v2.13.10 单头文件 `catch.hpp`，CI Worker 网络受限时下载失败（`status: 56`）导致 CMake configure 报错。同时上游 `tests/catch.hpp` 包装器在 `#else`（非 Catch3）分支用 `#include <catch2/catch.hpp>`（Catch2 v3 多文件布局路径），与本适配使用的 v2.13.10 单头文件不兼容。
   - **修改内容**：
     - `conanfile.py` 的 `source()` 阶段从 `conandata.yml` 的 `catch2` 段下载 Catch2 v2.13.10 单头文件并放置到 `tests/catch2/catch.hpp`，SHA256 与上游 CMake 期望值一致（`3725c0f0a75f376a5005dde31ead0feb8f7da7507644c201b814443de8355170`）。
     - `tests/CMakeLists.txt` 的 `else()` 分支把 `file(DOWNLOAD ...)` 替换为 `configure_file(${CMAKE_CURRENT_SOURCE_DIR}/catch2/catch.hpp ... COPYONLY)`，从本地源码树复制到 binary 目录。
     - `tests/catch.hpp` 包装器的 `#else` 分支改为 `#include "catch2/catch.hpp"`（本地相对路径），并提供函数式 `Contains` 包装器：`inline auto Contains(const std::string &x) { return Catch::Matchers::Contains(x); }`，规避 Catch2 v2.13.10 把 `Contains` 暴露为类（而非函数）导致的 clang 15 编译错误。

2. **修改的测试文件**：`tests/AppTest.cpp` 与 `tests/CMakeLists.txt`（通过 `patches/0002-guard-pthread-testcancel.patch` 应用）
   - **修改原因**：OHOS pthread 头文件未声明 `pthread_testcancel()`，`tests/AppTest.cpp:3042` 直接调用会导致编译失败。
   - **修改内容**：在 `tests/CMakeLists.txt` 的 `add_dependent_application_definitions` 函数开头新增 `check_function_exists(pthread_testcancel HAVE_PTHREAD_TESTCANCEL)` 探测，仅在探测成功时为 AppTest 目标定义 `HAVE_PTHREAD_TESTCANCEL`；`tests/AppTest.cpp` 中用 `#ifdef HAVE_PTHREAD_TESTCANCEL` 包裹该调用。该写法基于 POSIX 功能探测，不引入任何平台条件编译宏（符合项目 R8 规则）。真机验证显示探测结果为 `pthread_testcancel - not found`，`#ifdef` 自动跳过该调用，AppTest 正常通过。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已通过 CMake/CTest + Catch2 v2.13.10 提供完整测试覆盖。本适配额外保留 `test_package/test.cpp`，从 Conan 包消费者视角验证安装后的 CLI11 头文件、CMake 目标和公共 API 可正常使用，不属于对上游无测试场景的补全。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：24/24（100%）
- 新增测试用例通过率：4/4（100%）
- 本地 CI 验证：`zsh ci/conan/build_and_test.sh`（CI_PACKAGES=archives/c/CLI11/2.6.2）全部通过
  - L0 门禁（结构完整性）：pass
  - L1 门禁（测试执行验证）：pass（test_package executed）
  - L1e 反向验证（R34）：pass（test genuinely depends on CLI11）
  - L4 静态安全扫描：pass（patches clean）

## 补充说明

- CLI11 是 header-only 库，无外部运行依赖。
- 真机验证环境：HarmonyOS aarch64、Clang 15.0.4、CMake 4.1.2、Conan 2.29.1，`os.version=6.0`、`compiler.libcxx=libc++`、C++11。
- 主配方固定使用 `CMAKE_CXX_STANDARD=11` 和 `CMAKE_CXX_STANDARD_REQUIRED=ON`，确保测试配置及测试数量稳定。
- 主配方启用 `BUILD_TESTING=ON` 和 `CLI11_BUILD_TESTS=ON`，构建完成后通过 `cmake.test()` 执行完整上游 CTest 测试。
- **Catch2 注入策略**：上游测试依赖 Catch2 v2.13.10 单头文件，但 CI Worker 网络受限无法访问 `github.com/philsquared/Catch`。本适配通过 `conandata.yml` 的 `catch2` 段声明 Catch2 源 URL 与 SHA256，`conanfile.py` 的 `source()` 阶段预下载并放置到 `tests/catch2/catch.hpp`，补丁 `0001-use-local-catch2.patch` 让上游 CMake 从本地路径读取而非 `file(DOWNLOAD)`，同时修复 `tests/catch.hpp` 包装器与 v2.13.10 的 API 兼容性。
- `test_package` 在 `conan create` 测试阶段继续执行消费者测试，验证 `CLI::App` 实例化、`add_option`、`add_flag`、命令行解析及结果正确性。
- 使用 `self.settings.os in ("Linux", "OHOS")` 进行平台判断。
- 通过 CMakeToolchain 设置 `CMAKE_SYSTEM_NAME=Linux`，并使用 `str(self.settings.arch)` 动态设置 `CMAKE_SYSTEM_PROCESSOR`，规避 E092 并支持多架构构建。
- 补丁 `0002-guard-pthread-testcancel.patch` 遵循项目 R8 规则：不引入 `__OHOS__` 等平台条件编译宏，改用 CMake `check_function_exists` 进行 POSIX 功能探测，仅在探测成功时为 AppTest 定义 `HAVE_PTHREAD_TESTCANCEL`。
- 关联 Issue：Closes [#185](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/185)
