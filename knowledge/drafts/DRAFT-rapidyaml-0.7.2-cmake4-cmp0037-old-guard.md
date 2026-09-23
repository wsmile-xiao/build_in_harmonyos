# CMake >= 4.0 移除 `cmake_policy(SET CMP0037 OLD)`，需按版本号守卫

> 草稿（DRAFT）— 来源：rapidyaml 0.7.2 适配 HarmonyOS PC（commit 1f83cb45d9）

## 问题

CMake 4.x 之下，配置阶段报错：

```
CMake Error at .../c4Project.cmake:2872 (cmake_policy):
  Policy CMP0037 may not be set to OLD behavior because this version of CMake
  no longer supports it.  The policy was introduced in CMake version 3.0.0,
  and use of NEW behavior is now required.
```

上游 c4core v0.2.2 的 `cmake/c4Project.cmake` 为把 target 命名为 `test`（CTesting 保留字）
而无条件执行 `cmake_policy(SET CMP0037 OLD)`，在 CMake >= 4.0（OHOS 环境实测 4.1.2）被移除。

## 根因

- CMake 4.x 移除部分策略（含 CMP0037）的 OLD 兼容模式。
- 与 E187（`cmake_minimum_required < 3.5` 被拒、用 `CMAKE_POLICY_VERSION_MINIMUM`）同属
  CMake 4 兼容收紧，但本错误是"策略 OLD 模式被移除"，`CMAKE_POLICY_VERSION_MINIMUM` 无效，
  必须在源码内按版本守卫。

## 方案

```cmake
# 原来（破坏性）:
cmake_policy(SET CMP0037 OLD)  # target name "test" is reserved for CTesting

# 修复（版本守卫）:
if(CMAKE_VERSION VERSION_LESS 4.0)
    cmake_policy(SET CMP0037 OLD)
endif()
```

CMake >= 4 时跳过设置（默认 NEW 行为，target 不叫 test 即可）；CMake < 4 保持旧行为。

## 验证

- 补丁应用前：CMake 4.1.2 configure 失败（两次复现，日志见 conan-verify-report G2）。
- 补丁应用后：`conan create` 全门禁通过（conan-verify G2 PASS、finish W3 100%）。

## 适用边界

任何在 CMake >= 4.0 工具链下构建、上游 CMake 辅助模块设置 `CMP0037 OLD` 的 C/C++
库（c4core 系、rapidyaml，及复用 biojppm/cmake 辅助模块的项目）。

## 反例 / 禁止

- 无条件 `cmake_policy(SET CMP0037 OLD)` → CMake 4 下 configure 崩溃（本条目根因）。
- 无条件 `cmake_policy(SET CMP0037 NEW)` → 旧 CMake 下 target 名 `test` 冲突。

## 关系

- similar_to: E187（CMake 4 版本兼容类，但根因/解法不同）
- 配套草稿: DRAFT-rapidyaml-0.7.2-c4core-cmake-submodule-vendoring（c4core 子模块缺失，
  本条目是其 prerequisite 之一）