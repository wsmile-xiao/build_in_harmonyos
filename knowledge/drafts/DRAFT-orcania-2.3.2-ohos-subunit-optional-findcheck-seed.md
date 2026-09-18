# DRAFT-orcania-2.3.2-ohos-subunit-optional-findcheck-seed — OHOS 上 CMake+Check 库启用上游 CTest：Subunit 硬依赖可选化 + FindCheck 种子注入

> 对应 KV：`knowledge/drafts/DRAFT-orcania-2.3.2-ohos-subunit-optional-findcheck-seed.kv`
> 触发事件：orcania 2.3.2 HarmonyOS PC 适配（task_id `orcania-2.3.2-r01-pc2-25-20260916T133924Z`）

## 问题（error_signature）

OHOS 上以 CMake+Check（libcheck）为测试框架的 C 库，构建上游 CTest 树时：

```text
CMake Error: find_package(Subunit REQUIRED) 找不到 Subunit
（OHOS 无独立 Subunit 制品；conan check/0.15.2 自包含，不提供 Subunit）
```

上游 CMakeLists 在 `if (CHECK_FOUND)` 内用 `find_package(Subunit REQUIRED)` 硬性要求
Subunit（非 WIN32/APPLE 平台），OHOS 上没有对应的 Conan 制品 → CTest 树整个无法配置。

## 根因（root_cause）

- OHOS 生态无独立 Subunit 包；本项目的 conan libcheck（check/0.15.2）为自包含实现，
  官方 4 个测试程序只用 `check.h`，不需要 Subunit。
- 上游 CMake 却按 GNU/Linux 习惯把 Subunit 作为硬依赖 `find_package(Subunit REQUIRED)`，
  无 Subunit 时直接 FAIL，测试树无法启用。

## 解决方案（solution）

两层修复（互补，缺一不可）：

1. **patch（portability，CMakeLists.txt）**：`find_package(Subunit REQUIRED)` →
   `find_package(Subunit)`；并把 `list(APPEND TEST_LIBS Subunit::Subunit rt)`
   改为 `if (SUBUNIT_FOUND) list(APPEND TEST_LIBS Subunit::Subunit) endif()`
   （`rt` 仍无条件追加）。仅当测试程序确实只用 check.h 时才可去 REQUIRED。
2. **conanfile.py generate()/build()**：不启用 CMakeDeps 生成 check 的 config 包——
   conan toolchain 的 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` 会让 `find_package(Check)`
   以 CONFIG 模式命中 check 包自带 config（target `Check::check`），上游自己的
   `cmake-modules/FindCheck.cmake`（模块模式，`Check::Check` + `CHECK_FOUND`）永不执行，
   CTest 树被跳过。正确做法：不注入 CMAKE_PREFIX_PATH，改为向模块模式种子注入
   `CHECK_INCLUDE_DIR=<check_pkg>/include`、`CHECK_LIBRARY=<check_pkg>/lib/libcheck.a`。

## 验证（verification）

- conan-verify G2（conan create）通过；W3 本地 CI 通过（.ci-result.json exit_code=0）。
- CTest 4/4 通过（str_test/split_test/memory_test/pointer_list_test），
  51/51 源码声明用例全部实际运行并通过。
- 测试运行环境：可写 TMPDIR（libcheck fork IPC）+ LD_LIBRARY_PATH 指向 check 包 lib。
- 命令/日志：`ctest --test-dir build --output-on-failure`（exit 0），
  日志 /storage/Users/currentUser/tmp/orcania-2.3.2-ctest.log。

## 适用边界（boundary）

- 仅当：libcheck（check/0.15.2）自包含、官方测试程序只 include `check.h`、不调用
  subunit 专有 API 时，才能去掉 Subunit REQUIRED。若测试程序用 subunit 头/API，
  必须保留 Subunit 依赖（此时应改依赖注入而非去 REQUIRED）。
- 仅适用于静态构建（recipe 默认 shared=False 时启用上游测试；shared 构建跳过测试树）。
- CMakeDeps 禁用是硬条件：一旦生成 check-config.cmake，`CHECK_FOUND` 守卫失效。

## 反例（counter-example）

- 测试程序含 `#include <subunit.h>` 或链接 Subunit 符号的库 → 本方案不适用，
  需先解决 Subunit 制品可用性。
- 平台自带系统 libcheck 时（非 OHOS 主机），上游默认路径即可，无需种子注入。

## 关系（relations）

- `similar_to`: E515（refresh-patch/conandata patches 工具链，同为 OHOS 测试环境类）、
  E547（libcheck P_tmpdir 优先级，同为 check 测试框架环境故障）
- `caused_by`: OHOS 无独立 Subunit 制品 + conan libcheck 自包含
- `conflicts_with`: 无
- `prerequisite_of`: 无
