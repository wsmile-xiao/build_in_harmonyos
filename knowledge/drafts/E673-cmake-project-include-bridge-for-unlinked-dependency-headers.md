# E673 用 CMAKE_PROJECT_<name>_INCLUDE 给上游注入头文件桥接

> 状态: Draft（待审核 promote）| 日期: 2026-09-28
> 来源: feat/lapackpp-2024.10.26（conan create 实测，零补丁通过）
> 机器可读层: 同目录 `E673-cmake-project-include-bridge-for-unlinked-dependency-headers.kv`

## 现象

`lapackpp/2024.10.26` 适配中，配置阶段两个 `find_package` 相关失败：

```
CMake Error at conan/bridge_blaspp.cmake:11 (find_package):
  Could not find a package configuration file provided by "blaspp" ...
Call Stack (most recent call first):
  CMakeLists.txt:16 (project)

include/lapack/util.hh:15:10: fatal error: 'blas.hh' file not found
```

第一个说明构建树内没有 `blaspp-config.cmake`（配方没让 CMakeDeps 生成）；
第二个说明即便 find_package 成功，BLAS++ 的公共头也不在 include 路径上。

## 根因

两个独立缺口：

1. **没生成包配置**。上游 `find_package(blaspp)` 是硬要求（缺失即 `FATAL_ERROR:
   BLAS++ not found`）。配方里若只用 `CMakeToolchain(self)` 而不声明 `CMakeDeps`，
   构建树内不会有 `blaspp-config.cmake`。且在 recipe 中
   `self.generators.append("CMakeDeps")` **不生效**——`generators` 必须是类属性。
2. **上游不把导入目标链到自身**。`find_package(blaspp)` 之后 lapackpp 既不
   `target_link_libraries(lapackpp PUBLIC blaspp::blaspp)`，也不把
   `${blaspp_INCLUDE_DIRS}` 加进任何 target；CMake 不会因为"找到了包"就自动改
   别的目标的 include 路径。而 `include/lapack/util.hh:15` 用
   `#include "blas.hh"` 直接引用 BLAS++ 公共头。

原生构建里两者同前缀安装（`/opt/slate`），头落在编译器默认搜索路径，"不链也能找到"——
这是典型的"原生隐式成立、换包管理即失效"。

## 解法（零补丁，上游 CMakeLists 逐字未改）

用 CMake 官方注入点 **`CMAKE_PROJECT_<PROJECT_NAME>_INCLUDE`**：CMake 在 `project()`
之后**立即** include 该文件。配方用 `save()` 把桥接片段写到 source 树
（`conan/bridge_blaspp.cmake`），`generate()` 里指向它：

```cmake
if (NOT TARGET blaspp::blaspp)
    find_package(blaspp CONFIG REQUIRED)
endif()
include_directories(${blaspp_INCLUDE_DIRS})
```

要点：

- 用 `include_directories()`（**目录作用域**）而不是给某个 target 补 include——
  本包无法改上游 target 属性，而 `include_directories()` 在 `project()` 之后、
  `add_library` 之前生效，**自动覆盖其后创建的全部目标**。
- 变量名 `blaspp_INCLUDE_DIRS` 由 CMakeDeps 生成，用它而非手拼路径，保持依赖图单一事实源。
- 片段随 `export_sources` 进缓存，CI 从源码重建时同样可用，**无需下载任何额外产物**。
- 配套声明 `generators = "CMakeDeps"`（见上）。

同族变量还有 `CMAKE_PROJECT_INCLUDE`（所有 project 生效）与
`CMAKE_PROJECT_TOP_LEVEL_INCLUDES`（仅顶层工程），按需选。

## 实测证据（lapackpp/2024.10.26，2026-09-28）

桥接片段生效后 configure 出现
`Found BLAS++: .../b/build/Release/generators`，随后 200+ 个 TU 全部编译通过，
产出 `lib/liblapackpp.a`，`W3_RC=0 / 205s / 0 error`。

## 禁止

- ❌ `tc.variables["CMAKE_CXX_FLAGS"] = "-I<dep>/include"`：污染每一次编译（含
  `try_compile` 探针），丢失目录作用域控制，且把宿主绝对路径固化进配方。
- ❌ 用上游安装生成的 `<pkg>Config.cmake`（内嵌构建机绝对路径）。
- ❌ patch 上游 `CMakeLists.txt` 加 `target_link_libraries`：本场景零补丁可解，
  补丁会引入升级冲突面并触发 PF5/补丁审查。

## 对下游的直接复用

任何"上游 find_package(X) 只取变量、不链目标，却用引号包含引用 X 的公共头"的
CMake 工程，同一套 `CMAKE_PROJECT_<name>_INCLUDE` 桥接原样可用。
同类结构在 SLATE 本体、若干 Fortran/C++ 包装层也存在。
