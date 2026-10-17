# c4core 系 CMake 辅助子模块在官方 tarball 中缺失，需 export_sources 打包恢复

> 草稿（DRAFT）— 来源：rapidyaml 0.7.2 适配 HarmonyOS PC（commit 1f83cb45d9）

## 问题

源码配置阶段报错：

```
CMake Error at CMakeLists.txt:2 (include):
  include could not find requested file:
    ./ext/c4core/cmake/c4Project.cmake
```

或（同类根因链）：

```
c4core: unknown platform. CMAKE_SYSTEM_NAME=HarmonyOS
```

## 根因

GitHub source tarball 不含 git 子模块内容，只留空目录：

- rapidyaml v0.7.2 的 `ext/c4core` 是子模块（锁定 c4core commit `28d2b807` = tag v0.2.2）；
- c4core 自身的 `cmake/`（biojppm/cmake）、`src/c4/ext/debugbreak/`、`src/c4/ext/fast_float/`
  又各是子模块，tarball 中全部为空；
- rapidyaml 的 CMakeLists.txt 第 2 行就 `include(./ext/c4core/cmake/c4Project.cmake)`，
  tarball 解压后该文件不存在 → configure 直接失败。

## 方案

conan 配方把子模块内容作为出口资源打包，build() 恢复后再 configure：

1. 将 c4core `cmake/` 子模块的 22 个 `.cmake` 模块与 `debugbreak.h` 放入配方 `patches/`；
2. `export_sources()` 导出（确保干净构建可复现）；
3. `build()` 中复制回 `ext/c4core/cmake/` 与 `src/c4/ext/debugbreak/`；
4. `apply_conandata_patches`（HarmonyOS 平台分支 + CMP0037 守卫）后 cmake configure。

与 c4core/0.6.0 归档处理其自身子模块的模式一致。

## 验证

- 修复前：`include could not find requested file`（conan create 失败）。
- 修复后：`conan create` 干净构建通过（conan-verify G2 PASS、finish W3 100%）；
  本地 27069 个 gtest 用例全部通过。

## 适用边界

- 上游依赖 c4core 或 biojppm/cmake 辅助模块的 CMake 项目（rapidyaml、c4fs 等）；
- 任何构建辅助模块以 git 子模块形式存在、而官方 tarball 不含子模块内容的库。

## 反例 / 禁止

- 配方内 `git submodule update --init`：tarball 非 git 仓库，必然失败且 CI 不可复现。
- conandata 引用 `file://`、`.build-cache`、`predl_cache` 等本地路径（R39/PF7 源 URL 闸）。

## 关系

- similar_to: E150（发布 tarball 缺子模块内容）、DRAFT-release-tarball-missing-cmake-submodule
- prerequisite_of: DRAFT-rapidyaml-0.7.2-cmake4-cmp0037-old-guard（同 c4core 树内第二个修复）