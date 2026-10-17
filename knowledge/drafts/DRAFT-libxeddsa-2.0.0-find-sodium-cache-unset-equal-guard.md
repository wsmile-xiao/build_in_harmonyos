# 上游自带 Find 模块的 EQUAL 看门狗每次 configure 都 unset 缓存变量，-D 预置失效

- **草稿 ID**: DRAFT-libxeddsa-2.0.0-find-sodium-cache-unset-equal-guard
- **来源**: libxeddsa 2.0.0-20231128.d725c81 适配（读 FindSodium.cmake 源码发现守卫；改喂 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 后真机一次通过）
- **分类**: build / cmake / find-module / conan / dependency
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 2（configure 阶段 FATAL_ERROR，报错有误导性）

## 问题 / 错误签名

- conan 依赖（libsodium/1.0.22）已在图里，但 `cmake.configure()` 阶段
  `find_package(Sodium REQUIRED)` 报 `Could NOT find Sodium`
  （`sodium_LIBRARY_RELEASE-NOTFOUND`）。
- 通过 `tc.variables` / `-D` 预置 `sodium_INCLUDE_DIR`、`sodium_LIBRARY_RELEASE`
  看似最直接的喂路径方式，**完全无效**。

## 根因

libxeddsa vendor 的 `FindSodium.cmake` 开头有一个"变更跟踪守卫"（大量社区
Find 模块的通用写法）：

```cmake
if(NOT (sodium_USE_STATIC_LIBS EQUAL sodium_USE_STATIC_LIBS_LAST))
    unset(sodium_LIBRARY CACHE)
    unset(sodium_LIBRARY_DEBUG CACHE)
    unset(sodium_LIBRARY_RELEASE CACHE)
    ...
    set(sodium_USE_STATIC_LIBS_LAST ${sodium_USE_STATIC_LIBS} CACHE INTERNAL ...)
endif()
```

上游 `CMakeLists.txt` 在非 emscripten 分支 `set(sodium_USE_STATIC_LIBS NO)`。
CMake 的 `EQUAL` 做**数值**比较，对非数值字符串恒为 false → `NOT(false)`
恒为 true → **每次 configure 都无条件 unset 全部 `sodium_*` CACHE 条目**，
-D 注入的路径在 find_package 执行前就被清掉。find_library 只剩空 HINTS +
默认搜索路径，conan 包目录不在其中。

另注：conan `CMakeDeps` 生成的是 **config 模式**文件（`libsodium-config.cmake`），
而 `find_package(Sodium)` 走 **module 模式**（项目自带 FindSodium.cmake 已在
`CMAKE_MODULE_PATH`）——两者互不相干，"CMakeDeps 不生效"不是配置错误。

## 最小修复（真机验证）

不与看门狗对抗——它只删 `sodium_*` 条目，不碰 CMake 内建搜索变量。在配方
`generate()` 里：

```python
sodium = self.dependencies["libsodium"]
tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(sodium.package_folder, "include")
tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(sodium.package_folder, "lib")
tc.variables["CMAKE_PREFIX_PATH"] = sodium.package_folder   # 兜底
```

`CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH` 是 `find_path`/`find_library` 的
文档化搜索来源，与 unset 守卫正交。frp 真机 `conan create` 一次通过
（ctest 3/3 + test_package 20/20，链接的正是 ohpcd libsodium/1.0.22 静态库）。

## 影响面与推广

- 任何 vendor 了 Find 模块（FindSodium/FindXXX）并用 `<dep>_*_LAST` 内部
  cache 变量 + unset 守卫的上游；特征：模块前 50 行内出现 `_LAST` 与
  `unset(... CACHE)`。
- 识别口诀：**-D 喂不进去的 Find 模块，先查 unset 守卫，再喂内建搜索变量**。
- 备选修法：patch 掉守卫（改 STREQUAL）恢复 -D 能力，非必要不动上游文件。
