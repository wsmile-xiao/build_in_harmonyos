# DRAFT: CMAKE_SYSTEM_NAME=HarmonyOS 时 UNIX 变量为 FALSE——if(NOT UNIX) 平台分支误判

- **申请人/触发**: j669539（jinja2cpp 0.9 适配，patches/0001 第 2 项实测）
- **日期**: 2026-09-16
- **状态**: 草稿（待主编审定）

## 问题现象

OHOS SDK（clang 15.0.4，aarch64-linux-ohos）+ CMake 4.1.2 交叉构建时，
jinja2cpp 0.9 全部编译单元报：

```
clang-15: error: unsupported argument '-mbig-obj' to option '-Wa,'
```

且 `EXTRA_TEST_LIBS` 被设为 `stdc++`（应为 Threads::Threads）。

## 根因

CMake 平台变量 `UNIX` 按 `CMAKE_SYSTEM_NAME` 归属判定。HarmonyOS 不在
CMake 已知平台清单中，`CMAKE_SYSTEM_NAME=HarmonyOS` 时 `UNIX=FALSE`。
上游 `if (NOT UNIX)` 本意是"Windows/MinGW 平台"，鸿蒙下误判成立，
注入 MinGW 专用汇编参数 `-Wa,-mbig-obj`（clang 不支持）。

与 E092（CMake 不识别 HarmonyOS 平台名 → platform module 缺失）为相邻
主题不同错误：E092 是"平台检测失败"，本条目是"平台变量语义误判导致
分支走错"——错误签名（mbig-obj/分支行为）与修复动作（改判定条件）均不同。

## 解决方案

把"仅 Windows"语义的 `if (NOT UNIX)` 改为 `if (WIN32)`：

```cmake
if (${CMAKE_CXX_COMPILER_ID} MATCHES "Clang" OR ... MATCHES "GNU")
    if (WIN32)  # 原: if (NOT UNIX)
        set (EXTRA_TEST_LIBS "stdc++")
        set (CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS} "-Wa,-mbig-obj")
    else ()
        include(CMakeFindDependencyMacro)
        find_dependency(Threads)
        set (EXTRA_TEST_LIBS Threads::Threads)
    endif ()
```

OHOS/Linux/macOS 走 POSIX 分支（Threads::Threads），Windows/MinGW 保持
原行为。

## 兜底

配方 generate() 注入 `DUNIX=1` 缓存变量可欺骗简单 `if(NOT UNIX)` 判定，
但对反向 `if(WIN32)` 判定无效——治本需补丁改条件。

## 适用面预估

任何用 `if(NOT UNIX)` / `if(NOT UNIX AND NOT APPLE)` 做平台分支的 CMake
上游库在鸿蒙交叉构建下都可能踩中（grep GitHub CMakeLists 命中量巨大）。
跨库通用，非 jinja2cpp 专属。

## 验证

- jinja2cpp 0.9：补丁后 conan create 双路径全绿（with_tests 670/670）
- CI 构建：#48916（PR #10439，2026-09-17 校验通过：test_package 通过、L0/L1 门禁通过）
