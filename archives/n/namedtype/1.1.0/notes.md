# namedtype 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

上游是 INTERFACE（header-only）库，根 `CMakeLists.txt` 只
`add_library(NamedType INTERFACE)`，**没有 install 规则**；`ENABLE_TEST` 默认 ON，
`add_subdirectory(test)` 编译 `test/main.cpp` + 自带 `test/catch.hpp`（Catch1 单头）
并注册 CTest 目标 `NamedTypeTest`。

配方（`conanfile.py`）：

1. `source()`：`get()` 拉取 tag v1.1.0 归档（sha256 与 CCI 一致）；
2. `generate()`：`CMakeToolchain` 注入 `-DENABLE_TEST=ON`（钉死上游默认）；
   clang 未知告警名的处理由补丁 `0002` 在 `test/CMakeLists.txt` 内提供（见问题 2）；
3. `build()`：`apply_conandata_patches()` → `cmake.configure()` →
   `cmake.build()` → 真实执行 `build/test/NamedTypeTest`，并把 Catch 汇报的
   `All tests passed (N assertions in M test cases)` 与源码静态清点
   （`TEST_CASE` 数、断言宏数）**双向对账**，不等即失败（防 0 用例假绿）；
4. `package()`：复制 `include/NamedType/*.hpp` → `include/NamedType/`、
   `LICENSE` → `licenses/`（上游无 install 目标）；
5. `test_package/`：单头消费者测试，**只 include `<NamedType/named_type.hpp>`**，
   13 项断言，覆盖构造/算术/比较/`make_named`/`ref`/命名参数/`make_named_arg_function`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 单独 include `NamedType/named_type.hpp` 的消费者 TU 编译失败：`named_type_impl.hpp:110: error: no member named 'make_tuple' in namespace 'std'`（4 个公开头里 3 个失败） | `named_type_impl.hpp` 的 `details::AnyOrderCallable::operator()` 用 `std::make_tuple`/`std::get`，却只 `#include <type_traits>`、`<utility>`；上游测试 TU 因传递包含（`catch.hpp` 等）从未暴露该缺陷 | 补丁 `0001` 加一行 `#include <tuple>`（行为零变化）。消费者测试只 include 单头，构成该缺陷的回归面 |
| 2 | 上游测试目标编译直接硬错：`error: unknown warning option '-Wlogical-op' ... [-Werror,-Wunknown-warning-option]`（`-Wnoexcept`、`-Wstrict-null-sentinel`、`-Wuseless-cast` 同） | `test/CMakeLists.txt` 非 MSVC 分支写死一串 **GCC 专属** `-W*` 开关并配 `-Werror`；设备是 clang 15，未知告警名被 `-Werror` 放大成错误 | 补丁 `0002` 在该列表追加 `-Wno-unknown-warning-option`（只把「未知告警名」这一条诊断降级，其余 `-Werror` 告警面全部保留；先例 `a/asterisk-*`、`a/acpica/20251212` 同判据）。**放在补丁而非工具链注入**，使「解包 + 打补丁 + 裸 `cmake`」的 clean-verify(G0) 路径同样能构建成功（首轮曾用工具链注入，G0 裸建仍红，实测改补丁后 G0 通过）。实测全量测试编译 rc=0、**0 行告警日志** |

W0 生死关（版本可得性 / 硬依赖 / 平台可移植性）三关全过，逐条证据见
`$TASK_DIR/w0-evidence.md`（`#error`、ISA 专属头、glibc printf 钩子族全部 0 命中）。

## 源码修改

- `patches/0001-include-tuple-for-standalone-inclusion.patch`（`patch_type: compatibility`）
  - 目标：`include/NamedType/named_type_impl.hpp`
  - 内容：在 `#include <type_traits>` 前插入 `#include <tuple>`（+1 行）
  - 验证：`patch --dry-run -p1` rc=0；补丁无 CRLF、无 NUL、hunk 头 1 处
- `patches/0002-clang-unknown-warning-option.patch`（`patch_type: portability`）
  - 目标：`test/CMakeLists.txt`（**测试构建配置**，不触碰任何用例源码）
  - 内容：在 `target_compile_options(... -Weffc++)` 列表末尾追加
    `-Wno-unknown-warning-option` + 5 行解释性注释（+6 行）
  - 验证：`patch --dry-run -p1` rc=0；补丁无 CRLF、无 NUL、hunk 头 1 处；
    该开关对 GCC 是可忽略的 `-Wno-*` 形态（无其他诊断时才报），对 clang 只降级
    「未知告警名」诊断，**不削弱任何真实告警**
- 除上述两个补丁外**上游源码零改动**；上游测试源 `test/main.cpp`/`test/catch.hpp`
  **一字未改、一例未删、一例未跳过**（`test/CMakeLists.txt` 只加告警开关，用例与断言不变）。

## 依赖版本

零第三方依赖（上游 0 deps；header-only，无 `requires`/`tool_requires`）。
测试框架为上游自带 `test/catch.hpp`（Catch1 单头，随源码分发）。

## 验证结果

```bash
# 上游测试（配方 build() 内真实执行，运行期 == 静态清点）
All tests passed (78 assertions in 36 test cases)
# 静态清点：TEST_CASE=36、断言宏=78（REQUIRE 53 + CHECK 25）

# 消费者测试（test_package/test.cpp，单头自包含）
namedtype consumer test: 13/13 assertions passed
```

两表与取数命令见 `reports/test-report.md`。

**声明 N 的口径（rule4 下界）**：`N = max(本版本候选数法, 上游当前 HEAD 注册数) = max(78, 136) = 136`。
- 被审 tag v1.1.0：`test/main.cpp` 36 个 `TEST_CASE` / 78 处断言（运行期与静态清点相等，全部实跑通过）；
- 上游当前 HEAD（`master` @ `76668abe09807f92a695ee5e868f9719e888e65f`）：`test/tests.cpp` 82 个
  `TEST_CASE` / 136 处断言（HEAD 的 `test/main.cpp` 仅剩 1 行 `CATCH_CONFIG_MAIN`）；
- 差额 58 处断言 / 46 个用例 = v1.1.0 之后上游新增（被审版本源码树**不存在** `test/tests.cpp`，
  逐项清单见 `$TASK_DIR/upstream-head-count.md`，属「不可运行」而非「跳过」）；
  被删用例 0 个、两侧共有 36 个（被审 tag 的用例在 HEAD 全部仍在）。
- 分项自洽：上游 136 = PASS 78 + FAIL 0 + SKIP 0 + NOT_RUN 58；适配后 149 = PASS 91 + … + NOT_RUN 58。

## 注意事项

- **G0/E092 提示（已知、非阻塞）**：`CMAKE_SYSTEM_NAME` 被 conan 映射为 `HarmonyOS`，
  CMake 无对应 platform module，configure 打印
  `System is unknown to cmake, create: Platform/HarmonyOS …`。本包是 header-only +
  单 TU 测试，实测 configure/build/运行全部成功（G2 PASS、78/78 断言通过），
  与 `archives/c/crossdb/0.14.0` 同形态先例一致，故不注入 `-DCMAKE_SYSTEM_NAME=Linux`
  （改平台名会翻转 `CMAKE_CROSSCOMPILING` 并换掉整套平台模块，收益不明风险更高）。
- header-only 交付形态：按 `device-facts §二.17`，`conan-verify` 的 G4/L2/L4/L5
  对无 `bin/`、无 `lib/` 的包会走「跳过」分支却并列打印 ✅；跳过行按 SKIPPED
  对待，人工补测记录在 `reports/conan-verify-supplement.md`。
- 上游 `ENABLE_TEST` 默认 ON，任何一次配方构建都会编译并运行上游测试，
  不会出现「测试未接线」的静默跳过。
