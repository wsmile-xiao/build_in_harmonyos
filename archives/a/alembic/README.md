# Alembic

## 简介

Alembic 是由 Sony Pictures Imageworks 与 Industrial Light & Magic 联合开发的开源计算机图形交换框架，用于在 VFX/动画流水线中高效存储与共享 3D 数据（几何体、灯光、相机、材质等）。它以稳定的 Ogawa/HDF5 归档格式保存场景的离散采样，广泛用于 Maya、Houdini、Arnold、RenderMan 等工具间的数据传递。

## 功能概述

- **归档格式**：Ogawa（默认，高性能）与 HDF5（可选）两种后端
- **核心库 libAlembic**：提供 Abc / AbcGeom / AbcMaterial / AbcCoreAbstract / AbcCoreOgawa / AbcCoreLayer / Ogawa / Util 等模块的 C++ API
- **命令行工具**：AbcLs / AbcTree / AbcConvert 等（本次适配未构建，见下）
- **依赖**：仅需 Imath 数学库

## OHOS 适配

### 适配要点

1. **Imath 内嵌编译**：Alembic 唯一硬依赖 Imath 未发布到 OHOS Conan 制品仓，故在配方中 vendor Imath 3.1.12 源码，单独用同一 Conan 工具链 cmake 构建并安装到本地 prefix，再由 Alembic 的 `FIND_PACKAGE(Imath)` 经 `CMAKE_PREFIX_PATH` 解析。两者静态库 + 头文件一并打包
2. **规避 target_compile_features**：CMake 4.x 无法识别 OHOS clang（compiler id 为 unknown，`CMAKE_CXX_COMPILE_FEATURES` 为空），对 vendored Imath 应用 `0001-imath-cxx-standard.patch`，将 `target_compile_features` 改为 `CXX_STANDARD` 属性
3. **静态构建**：`ALEMBIC_SHARED_LIBS=OFF`（Alembic 自有选项，非 `BUILD_SHARED_LIBS`），规避 OHOS 共享库 RPATH 问题
4. **仅产出库**：`USE_BINARIES=OFF`，不构建缺乏统一 `--version` 接口的 Abc* 命令行工具；库功能由 test_package 与上游 ctest 覆盖
5. **禁用可选组件**：`USE_HDF5/USE_ARNOLD/USE_PRMAN/USE_MAYA/USE_PYALEMBIC` 均 OFF
6. **上游测试**：`USE_TESTS=ON`，build() 内 `cmake.test()` 运行 57 个 ctest 用例，全部通过

### 已知限制

- HDF5 后端的 7 个测试用例因 `USE_HDF5=OFF`（HDF5 依赖未提供）不参与编译/运行
- 不构建 Abc* 命令行工具（库适配范畴之外）

## 依赖

### 编译依赖（vendor 源码，非 Conan 包）

- Imath 3.1.12（vendor 进构建，打包为 libImath.a + include/Imath/）
