# ctre 3.11.0 适配笔记

> 库类型：header-only（无需编译，仅安装头文件）。Apache-2.0-with-LLVM-exception。

## 官方来源核验

- 官方仓库: https://github.com/hanickadot/compile-time-regular-expressions
- 正式标签: `v3.11.0`
- 源码 tarball: `https://github.com/hanickadot/compile-time-regular-expressions/archive/v3.11.0.tar.gz`
- SHA-256: `7d4b30d0bdd8864a47cceb2ab8e7c4d1846f0ec62383f8c45122435d32f19530`（conan-center-index 同版本实测值）
- 相对 3.10.0 的上游变更：更新实验性 CMAKE_IMPORT_STD 标志

## 结构

- header-only：`include/ctre.hpp`、`include/ctre-unicode.hpp`、`include/ctll.hpp`、`include/unicode-db.hpp` 及 `include/ctre/*.hpp`、`include/ctll/*.hpp`、`include/unicode-db/*.hpp`
- CMake：INTERFACE 目标 `ctre` / `ctre::ctre`，`CTRE_CXX_STANDARD` 默认 20；配方显式设为 17（与 ohos-aarch64 profile 的 compiler.cppstd=17 对齐）
- 上游自带 `.conan/` 为 Travis 时代 ConanMultiPackager，不可直接用于 Conan 2.x，本配方重写
- 上游测试：`tests/*.cpp` 共 25 个编译期断言翻译单元，由 CMake 聚合目标 `ctre-test` 驱动（`tests/CMakeLists.txt` 对每个 .cpp 建 STATIC 库，EXCLUDE_FROM_ALL）；`tests/benchmark*` 不计入默认目标。计数口径：`ls tests/*.cpp | wc -l` = 25

## 补丁

- 无补丁（v3.11.0 原生通过）。曾尝试 finish_hexdec 固定 0x7F 阈值补丁，真机证明方向错误已撤销：上游库与测试均为平台自适应，OHOS/aarch64 上 char 为 unsigned 时两侧一致取 character<char>，原生即通过；强行固定 0x7F 反而使库产出 char32_t 与测试期望 char 失配，导致 tests/generating.cpp:60-62 static_assert 失败。

## 上游测试接入

- `conanfile.py build()`：`CMakeToolchain` 设 `CTRE_BUILD_TESTS=ON`、`CTRE_BUILD_PACKAGE=OFF`、`CTRE_CXX_STANDARD=17`，`cmake.configure()` 后 `cmake.build(target="ctre-test")` 完整编译 25 个测试单元，成功即全部通过（编译期 static_assert），随后输出 `HMBS_UPSTREAM_TEST_RESULT`（framework=`cmake-ctre-test`，discovered/executed/passed=25）并落盘 `build_folder/hmbs_upstream.json`；`package()` 将其拷贝到 `package/res/hmbs_upstream.json` 供 test_package 在缓存命中轮复发。
- 真机 cmake 4.4.3 兼容：上游根 CMakeLists 在 CMake>=4.0.3 时强制 `CMAKE_CXX_MODULE_STD=1`，OHOS clang 工具链无 import-std 支持，configure 在首个测试目标（`ctre-test-__utf8`）报错；配方在 `generate()` 预设 `CMAKE_EXPERIMENTAL_CXX_STD=ON` 跳过上游该分支并显式关闭 `CMAKE_CXX_MODULE_STD`/`CMAKE_EXPERIMENTAL_CXX_IMPORT_STD`（`CTRE_MODULE=OFF`，头文件与测试均不用模块，仅恢复 pre-4.0 行为，不裁剪任何测试单元）。
- 证伪说明：若把被测头文件替换为桩，`ctre-test` 编译失败即 build() 抛错，不会静默通过；`tests/generating.cpp` 的 hexdec 高字节断言是反向证据（有错误 0x7F 补丁时在 unsigned-char 平台必红，原生无补丁时通过）。

## test_package

- `test_package.cpp`：4 个真实 API 检查（`ctre::match` 编译期 static_assert + 运行时 `search` 子串 + 数字提取 + 命名捕获组），二进制自身计数并打印 `HMBS_TEST_PACKAGE_RESULT`（discovered=4/passedCount=实测通过数）。
- `conanfile.py test()`：`cmake.test()`（ctest 注册 1 项）+ 直接运行二进制（L0d 的 self.run 证据），随后读取 `package/res/hmbs_upstream.json` 复发 `HMBS_UPSTREAM_TEST_RESULT`（缓存命中轮兜底）。

## 依赖版本

- 构建依赖：无（纯模板 + 标准库；cmake 由 HMBS 预检注入系统版本，不声明 tool_requires）
- 编译器：clang 15 / libc++ / C++17（ohos-aarch64 profile）

## 验证结果

- 待 HMBS 真机预检返回后填写（conan create 日志中的 ctre-test 25/25 与 test_package 4/4 实测值）。

## 注意事项

- 本轮未提交、未推送，等待 HMBS 后台真机验证。
- Windows 工作区存在 `archives/l/libXext` 与 `archives/l/libxext` 大小写冲突，已对后者 `git update-index --assume-unchanged` 以保持本任务 `git status` 干净；该标记仅影响本地索引，不进入提交内容。
