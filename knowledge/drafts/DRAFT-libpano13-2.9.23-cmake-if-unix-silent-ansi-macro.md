# DRAFT-libpano13-2.9.23-cmake-if-unix-silent-ansi-macro

## 错误特征

上游 CMake 库编译报 GUI 头文件缺失：

```
In file included from .../PTDialogs.c:35:
.../sys_X11.h:22:10: fatal error: 'libgimp/gimp.h' file not found
#include <libgimp/gimp.h>
         ^~~~~~~~~~~~~~~~~
```

连带 `gtk/gtk.h` 同样缺失（sys_X11.h 头部同时 include 两个 GUI 头）。

## 触发条件

- CMake 库的 CMakeLists 用 `IF(UNIX) ADD_DEFINITIONS(-D<平台宏>)` 控制功能宏
- C 源码用 `#if !__Mac__ && !__Win__ && !__Ansi__` 类平台宏选择 GUI/X11 分支
- OHOS 工具链下 `CMAKE_SYSTEM_NAME=HarmonyOS`，`UNIX` 变量为假 → 宏静默未定义
- 无 GUI 依赖的纯 ANSI/终端分支存在（如 libpano13 的 sys_ansi.h）

libpano13 2.9.23 实证：`CMakeLists.txt` 第 140-141 行 `IF(UNIX) ADD_DEFINITIONS(-D__Ansi__)`，
`PTDialogs.c` 第 34-35 行 `#if !__Mac__ && !__Win__ && !__Ansi__` 落入 `sys_X11.h`。

## 根因

CMake 在 OHOS 工具链下 `CMAKE_SYSTEM_NAME` 为 "HarmonyOS"，它不是 WIN32 也不是 UNIX。
`IF(UNIX)` 条件不成立，`ADD_DEFINITIONS(-D__Ansi__)` 静默跳过（无任何报错）。
源码条件编译因 `__Ansi__` 未定义而走 X11 分支，include 上游假定存在的 GUI 头。

与 E532 同根（CMake UNIX 变量在 OHOS 为假），但 E532 是三分支显式
`if(WIN32)/elseif(UNIX)/else() FATAL_ERROR "Unsupported platform"`，错误在 configure 期
显式暴露；本条目是 `IF(UNIX)` 单分支静默不生效，功能宏缺失导致编译期 GUI 头报错。

## 解决方案

在 conanfile.py `build()` 的 cmake 参数中追加：

```python
defs.append("-DCMAKE_C_FLAGS=-D__Ansi__")
```

让 C 源码条件编译选择纯 ANSI 分支（sys_ansi.h，无 GIMP/GTK/X11 依赖）。不改上游源码、
不打补丁；功能宏由编译标志注入，绕开依赖 UNIX 变量的 ADD_DEFINITIONS。

`-D__Ansi__` 是 libpano13 上游既有平台宏（`__Ansi__` 语义 = 纯 ANSI 控制台分支），
不属于新增 `__OHOS__` 宏，也不违反 R8 patches 禁平台宏规则（未打补丁）。

## 验证证据

- 修复前：`PTDialogs.c:35` → `sys_X11.h:22` → `libgimp/gimp.h not found`，`make` 中止
- 修复后：`make` 100% 完成，`ctest` 8/8 通过，`conan create` 全流程通过

## 与已有条目的关系（部分重复）

- **重合点（E532）**：根因相同——CMake 在 OHOS 上 `UNIX` 变量为假，平台判定分支行为改变。
- **差异点**：
  - E532 场景：显式三分支落入 else()，configure 期 FATAL_ERROR "Unsupported platform"，方案是
    改 CMakeLists 分支条件（`elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`）；
  - 本条目场景：`IF(UNIX)` 静默不生效导致功能宏缺失，编译期 GUI 头报错，方案是 conanfile
    注入 `-DCMAKE_C_FLAGS=-D__Ansi__` 切回纯 ANSI 分支，无需 patch。
- **新增价值**：为"无 GUI 分支可选、仅需恢复功能宏"的库提供最小侵入修复路径（编译标志注入），
  与 E532 的"改平台分支"互补。关联 E463（GTK GUI 头/运行环境的 headless 处理）作为同族参照。

## 适用边界

- ✅ 上游 CMakeLists 用 IF(UNIX) 控制功能宏、源码有纯 ANSI 分支可选
- ✅ 只缺功能宏、不改平台行为即可编译的场景（libpano13 2.9.23 实证）
- ⚠️ 若源码没有 ANSI 分支、X11 分支是唯一实现，则需 E532 式改分支或裁剪 GUI 功能
- ❌ 不得伪造 `__OHOS__` 宏或注入与上游语义冲突的宏名
