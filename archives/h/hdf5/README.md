# HDF5

## 简介

HDF5（Hierarchical Data Format version 5）是一个高性能的数据管理和存储套件，专为科学和工程数据的存储、管理和访问而设计。它支持复杂的数据对象、元数据和高效 I/O，广泛应用于气象、航空航天、生物医学等领域。

## 功能概述

- **层次化数据结构**: 支持类似文件系统的组（Group）和数据集（Dataset）组织方式
- **高效 I/O**: 支持并行 I/O、数据压缩、分块存储
- **跨平台**: 支持 Linux、Windows、macOS 等多种操作系统
- **多语言支持**: 提供 C、C++、Fortran、Python、Java 等语言接口
- **元数据管理**: 灵活的属性（Attribute）系统存储元数据
- **大数据支持**: 可处理 PB 级数据

## OHOS 适配

### 适配要点

1. **构建系统选择**: HDF5 同时支持 Autotools 和 CMake。在 OHOS 上推荐使用 CMake 构建系统。

2. **TRY_RUN 处理**: CMake 检测到交叉编译时会执行 TRY_RUN 测试。需要创建 `TryRunResults-ohos.cmake` 缓存文件预先设置测试结果。

3. **平台检测**: 使用 `CMAKE_SYSTEM_NAME=Linux`（而非 OHOS）绕过 CMake 的平台未知警告。

4. **依赖指定**: 需要手动指定 zlib 的路径：
   ```cmake
   -DZLIB_INCLUDE_DIR=/path/to/include
   -DZLIB_LIBRARY=/path/to/libz.a
   ```

5. **测试禁用**: OHOS 平台限制可能导致部分测试文件复制失败，建议禁用测试和示例构建：
   ```cmake
   -DBUILD_TESTING=OFF
   -DHDF5_BUILD_EXAMPLES=OFF
   ```

### 已知问题

- **config.status 权限问题**: Autotools 构建在 OHOS 上可能遇到临时文件创建失败，建议使用 CMake
- **HAVE_TM_ZONE 测试**: 需要在 HDFTests.c 中添加测试定义
- **long double 精度**: musl 的 LDBL_DIG 为 33，需正确设置

## 依赖关系

### 编译依赖

- **zlib**: 压缩支持（必需）
- **szip**: 可选压缩库（当前未启用）

### 运行依赖

- zlib（动态链接时）

## 提供的库和工具

### 库文件

- `libhdf5.a` / `libhdf5.so` - 核心库
- `libhdf5_cpp.a` / `libhdf5_cpp.so` - C++ 绑定
- `libhdf5_hl.a` / `libhdf5_hl.so` - 高级 API
- `libhdf5_hl_cpp.a` / `libhdf5_hl_cpp.so` - 高级 API C++ 绑定

### 工具

- `h5dump` - 查看 HDF5 文件内容
- `h5ls` - 列出 HDF5 文件结构
- `h5cc` - HDF5 C 编译器包装脚本
- `h5c++` - HDF5 C++ 编译器包装脚本
- `h5copy` - 复制 HDF5 对象
- `h5diff` - 比较 HDF5 文件
- `h5repack` - 重打包 HDF5 文件
- 等 20+ 工具

## 参考资料

- 官网: https://www.hdfgroup.org/solutions/hdf5/
- 文档: https://portal.hdfgroup.org/display/HDF5/
- 源码: https://github.com/HDFGroup/hdf5
- 下载: https://download.savannah.nongnu.org/releases/hdf5/