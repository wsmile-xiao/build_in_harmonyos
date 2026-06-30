# apache-arrow 24.0.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-05-26
- 编译器: clang/clang++ (15.0.4)
- 状态: built ✅

## 编译步骤

### 1. 源码准备
- 源码包: apache-arrow-24.0.0-full.tar.gz (17.2MB)
- 包含完整的 Arrow C++ 核心库（cpp/ 目录）
- 注意：之前的 apache-arrow-24.0.0.tar.gz 只是 Arrow GLib（C 绑定）

### 2. CMake 配置
关键配置参数：
```bash
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_SYSTEM_NAME=Linux \
      -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_BUILD_TYPE=Release \
      -DARROW_BUILD_TESTS=OFF \
      -DARROW_WITH_PYTHON=OFF \
      -DARROW_WITH_JAVA=OFF \
      -DARROW_BUILD_SHARED=ON \
      -DARROW_BUILD_STATIC=ON ..
```

**重要发现**：
- 必须设置 `CMAKE_SYSTEM_PROCESSOR=aarch64`，否则 CMake 会报错 "Unknown system processor"
- Arrow 会自动下载并编译依赖：xsimd、mimalloc
- 使用 vendored 模式处理第三方库

### 3. 编译执行
- 命令: `make -j2`
- 耗时: 725.4秒（约12分钟）
- 编译产物：
  - libarrow.so.2400.0.0 (16MB 动态库)
  - libarrow.a (33MB 静态库)
  - libarrow_bundled_dependencies.a (311KB)

### 4. 安装
- DESTDIR 模式安装到 staging 目录
- 最终安装到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报错 "Unknown system processor" | 设置了 CMAKE_SYSTEM_NAME=Linux 但没有 CMAKE_SYSTEM_PROCESSOR | 添加 -DCMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | xsimd 依赖缺失 | Arrow 需要但未安装 | 使用 vendored 模式自动下载编译 |
| 3 | mimalloc 依赖缺失 | Arrow 默认使用 mimalloc 内存分配器 | 使用 vendored 模式自动下载编译 |

## 关键发现

### Apache Arrow 源码结构
- **apache-arrow-24.0.0-full.tar.gz**: 完整源码，包含 cpp/ 目录（Arrow C++ 核心库）
- **apache-arrow-24.0.0.tar.gz**: 仅 Arrow GLib（C 绑定），不含 C++ 核心

### 编译配置要点
1. **必须设置处理器类型**: CMAKE_SYSTEM_PROCESSOR 必须与目标架构匹配
2. **禁用测试**: ARROW_BUILD_TESTS=OFF 可大幅减少编译时间
3. **IPC 支持**: Arrow IPC 默认启用（ARROW_IPC=ON）
4. **内存分配器**: Arrow 使用 mimalloc（ARROW_MIMALLOC=ON）

### 编译产物说明
- **libarrow.so**: Arrow C++ 核心库（包含 array、compute、ipc 等模块）
- **头文件**: 完整的 Arrow C++ API（arrow/api.h、arrow/array.h 等）
- **CMake 配置**: ArrowConfig.cmake 供其他项目使用

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- xsimd: 14.0.0 (vendored)
- mimalloc: 3.2.7 (vendored)

## 验证结果

✅ 编译成功
✅ 安装到 ~/usr/local 完成
✅ 产物完整：lib/libarrow.so、lib/libarrow.a、include/arrow/
✅ CMake 配置可用：lib/cmake/Arrow/ArrowConfig.cmake
✅ pkg-config 可用：lib/pkgconfig/arrow.pc
**编译耗时**: 725.4秒
**安装位置**: ~/usr/local
---

**编译结束**: 2026-05-26 21:22
**最终状态**: built
