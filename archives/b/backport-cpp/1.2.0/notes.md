# backport-cpp 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，INTERFACE 目标 `Backport::Backport`）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK / device + CI worker 同源）；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, libc++, cppstd=17, Release）
- 状态: built（verify 通过、未 upload；O5 口径：合并 + release upload 确认前不写 published）

## 源与身份（W0 三路实核）
- 上游 tag: `git ls-remote --tags https://github.com/bitwizeshift/BackportCpp` →
  `3ad66bfe… refs/tags/v1.2.0`（注解标签）→ `e5184de86940aae8b61a7578ced3ac02a5639657 refs/tags/v1.2.0^{}`
- 源 tarball: 平台 sourceUrl = `https://github.com/bitwizeshift/BackportCpp/archive/refs/tags/v1.2.0.tar.gz`，166430 字节
- sha256: `8efded40a1d0e6674824336499d8706043a62bd8ae8aef62210c8c215f710b84`
  —— 本机实测 == conan-center-index `recipes/backport-cpp/all/conandata.yml` 记录值（逐字一致）
- 依赖: 0（运行期）；上游单测需 Catch2 2.x → ohpcd 制品仓 `catch2/2.13.10` 已发布
- W0-3 平台不可移植判据：ISA 专属头 / ISA 关键字 / glibc printf 钩子 / 内联汇编 四组 grep 全部 0 命中

## 编译步骤

1. `conan create archives/b/backport-cpp/1.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build=missing`
2. 配方 `source()`：`get()` 官方 tarball（strip_root）→ `apply_conandata_patches()` 打 `patches/0001-fix-qualified-destructor-names.patch`
3. `generate()`：CMakeToolchain 注入 `BACKPORT_COMPILE_UNIT_TESTS=ON`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`，并把注入的最小 `Catch.cmake` 所在目录写进 `CMAKE_MODULE_PATH`
4. `build()`：`cmake.configure()` → `cmake.build()`（13 个测试源 + 26 个头文件自包含 OBJECT 目标）→ 直跑 `Backport.test --durations yes` → `cmake.test()`（ctest 走上游 catch_discover_tests 注册面）
5. `package()`：拷 `include/**.hpp`（27 个：16 公开头 + 11 个 detail 头）+ `LICENSE` 到 `licenses/`
6. `test_package`：CMakeDeps 解析 `find_package(Backport)` → 消费者 `test_backport_cpp`（C++11）编译并运行，自报 35/35

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 15 编译上游单测报 `error: ISO C++ requires the name after '::~' to be found in the same scope as the name before '::~' [-Werror,-Wdtor-name]`（optional.hpp:994、detail/variant_base.hpp:217） | 上游两处**类外析构函数定义**写成 `bpstd::detail::X<...>::~X()`，在上游自带的 `-pedantic -pedantic-errors` 下触发 ISO 名字查找诊断（旧工具链不报） | `patches/0001-fix-qualified-destructor-names.patch` 按 clang fix-it 补写注入类名：`…<false>::optional_base::~optional_base()`；**纯名字查找形式修正、零语义变化，用例数与断言数不变**。修后 16 个公开头在 `-pedantic-errors` 下逐个编译探针 16/16 通过 |
| 2 | 上游 `test/CMakeLists.txt` configure 失败：`include could not find requested file: Catch` | 上游调用 `include(Catch)` + `catch_discover_tests()`（Catch2 v2 的 `contrib/Catch.cmake`）；ohpcd 的 `catch2/2.13.10` 只打包头文件（`include/catch2/*.hpp`），不含该模块 | 按 `archives/c/ctpg/1.3.7` 先例在 `generate()` 注入最小 `Catch.cmake`（`add_test(NAME <target> COMMAND <target> --durations yes)`），**不改上游源码**；Catch2 自报口径由 `build()` 直跑采集 |
| 3 | 上游 `cmake/AddSelfContainmentTest.cmake:1` 自带 `cmake_minimum_required(VERSION 3.1)` | 设备/CI 的 CMake 4.x 收紧旧策略兼容 | `generate()` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 自身变量，不改上游文件） |
| 4 | `test/CMakeLists.txt` 的 `set_target_properties(${UNITTEST_TARGET_NAME} …)` 变量未定义 | 上游笔误，展开为空参数 | 实测 CMake 接受零 target 形态（配置通过），**不改上游**，登记为观察项 |

## 源码修改

- `patches/0001-fix-qualified-destructor-names.patch`（2 个 hunk，各 1 行）
  - `include/bpstd/optional.hpp:994` 析构定义补写注入类名
  - `include/bpstd/detail/variant_base.hpp:217` 同上
  - `patch_type: portability`；无 `__OHOS__`、无平台宏、无 `#ifdef` 分支

无其他源码修改；上游 13 个测试源与 26 个头文件自包含清单**零改动**。

## 依赖版本

- 运行期: **0**
- 构建期（仅上游单测）: `catch2/2.13.10`（ohpcd 制品仓，header-only，package_id `da39a3ee…`）
- 工具链: clang/clang++ 15.0.4、CMake 4.1.2、GNU Make 4.4.1

## 上游测试统计（口径见 `test_package/MANIFEST.yml`）

- **N（上游用例总数）= 194** = 168 个 Catch2 `TEST_CASE` 行 + 26 个头文件自包含编译用例
  - 取数命令① `grep -rh 'TEST_CASE' test --include='*.cpp' | wc -l` → **168**
  - 取数命令② 根 `CMakeLists.txt` `header_files` 条数 → **26**
  - rule4 下界核对：上游当前 HEAD（`169d7fa`, 2025-05-06）同一命令同样 168 / 26，**无差额**
- **N′（本次实际执行）= 194**，失败 0、跳过 0、未运行 0
- Catch2 运行期自报（同一二进制直跑）: `All tests passed (682 assertions in 168 test cases)`
- ctest（上游 catch_discover_tests 注册面，注入实现）: `100% tests passed, 0 tests failed out of 1`
- 消费者测试（鸿蒙特有测试行，**不进上游分母**）: `PASS: backport-cpp 1.2.0 消费者测试 35/35 断言通过`
  （35 条运行期 CHECK；另有 3 条编译期 static_assert 只做编译期保障、不计入运行期总数；一个 TU 包含全部 16 个公开头）

## 上游测试原始日志摘录（reports/conan-create.log 逐字）

```
All tests passed (682 assertions in 168 test cases)

Running tests...
Test project /storage/Users/currentUser/.conan2/p/b/backpe9c724f61fde5/b/build/Release
    Start 1: Backport.test
1/1 Test #1: Backport.test ....................   Passed    0.09 sec
100% tests passed, 0 tests failed out of 1
Total Test time (real) =   0.10 sec

backport-cpp/1.2.0: package(): Packaged 27 '.hpp' files
backport-cpp/1.2.0: package(): Packaged 1 file: LICENSE

backport-cpp/1.2.0 (test package): RUN: "./test_backport_cpp"
PASS: backport-cpp 1.2.0 消费者测试 35/35 断言通过
```

## 验证结果

```bash
# 采信轮（清缓存 → conan-verify → 证据副本 → finish 前快照）
sh "$HOME/ws/tools/conan_verify_round.sh" backport-cpp 1.2.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
# 上游测试通过率（N/N′ 同口径）：194/194（100%）
# 消费者测试通过率：35/35（100%）
```

## 注意事项

- 分支 `feat/backport-cpp-1.2.0` 与平台登记名/包目录名逐字符一致（分支名门禁）
- 本包是**全新包**（upstream/main 无 `archives/b/backport-cpp`），`task_init.sh` 需 `--allow-unpublished`
- `manifest.yaml` 的 `status: built`（O5：合并 + release upload 确认后才 `published`）
- `reports/` 被 `.gitignore` 忽略，证据不进 PR；PR 正文用例数全部由本轮设备日志复算
- 上游 `test/CMakeLists.txt` `set_target_properties(${UNITTEST_TARGET_NAME} …)` 空变量：CMake 实测接受，登记观察不改上游
