# silo-llnl

Silo 是 Lawrence Livermore National Laboratory (LLNL) 开发的一个库，用于将多种科学数据（网格、场、材料、曲线等）以二进制文件（磁盘或内存 in-situ）形式读写。

## 功能概述

- PDB 与 HDF5 两种数据库驱动（HDF5 驱动需 HDF5 依赖）
- 支持多种网格类型（结构/非结构多块、AMR、曲线等）与场变量
- 支持压缩、命名 scheme、多块数据库、部分 I/O 等高级特性

## OHOS 适配

- 4.12.x 起为纯 CMake 构建（已移除 autotools）
- CMake 无 HarmonyOS 平台模块，需 `CMAKE_SYSTEM_NAME=Linux` 别名以启用 `if(UNIX)` 分支（E092 模式）
- 启用 HDF5 时库输出名为 `libsiloh5`（含 PDB 驱动），consumers 需链接 `siloh5` 并传递链接 HDF5
- `SILO_BUILD_FOR_BSD_LICENSE=ON` 关闭 fpzip/hzip（无 zlib 依赖），许可证保持 BSD-3-Clause
- Fortran / Python / JSON / Browser / Silock / Silex 组件在 OHOS 上禁用（无 gfortran / Qt6 / json-c）
- 静态构建（`SILO_ENABLE_SHARED=OFF`）规避 silo 测试使用的 macOS 专属 `@loader_path` RPATH 在 Linux 上失效的问题

## 依赖关系

- 编译/运行依赖：`hdf5`（发布版 hdf5/1.13.0）
- 无其它外部依赖（BSD 构建关闭 fpzip/hzip 后无需 zlib）

## 参考资料

- 官网: https://silo.llnl.gov
- 源码仓库: https://github.com/llnl/Silo
- 版本: 4.12.1
