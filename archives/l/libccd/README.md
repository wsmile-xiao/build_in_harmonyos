# libccd 2.1 — OpenHarmony 编译记录

## 基本信息
- **软件**: libccd
- **版本**: 2.1
- **构建系统**: CMake
- **目标平台**: ohos-aarch64
- **编译状态**: success

## 软件介绍

libccd 是一个用于两个凸形状之间碰撞检测的库。支持多种碰撞检测算法，包括 MPR (Minkowski Portal Refinement) 和 GJK (Gilbert-Johnson-Keerthi)。

## 编译指导

### 前置条件
- CMake 3.5+
- Clang 15.0.4 (OpenHarmony SDK)
- 无额外依赖

### 编译命令
```bash
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
make test  # 可选测试
make install DESTDIR=/path/to/staging
```

### 注意事项
1. OpenHarmony 使用 musl libc，libm/librt 已内置在 libc 中
2. CMake 需要版本 3.5+ 以兼容 CMake 4.x

## 补丁清单

| 补丁文件 | 说明 | 类型 |
|----------|------|------|
| 0001-CMakeLists.txt.patch | cmake_minimum_required VERSION 升级到 3.5 | 平台兼容 |
| 0002-src-CMakeLists.txt.patch | libm 可选检查 (musl libc) | 平台兼容 |
| 0003-src-testsuites-cu-CMakeLists.txt.patch | librt 可选检查 (musl libc) | 平台兼容 |

## 已知限制

- G0 干净构建验证因构建系统检测问题未能通过（系统检测为 autotools 但实际是 cmake）
- 不影响实际编译和使用

## 功能验证

```bash
# 检查库文件
ls -la /usr/local/lib/libccd.so

# 检查 pkg-config
pkg-config --cflags ccd
pkg-config --libs ccd

# CMake 使用
find_package(ccd REQUIRED)
target_link_libraries(your_target ccd)
```

## 相关知识

- E011: CMake find_library 无法找到 libm/librt (musl/OpenHarmony)

## 下载

预编译包位于 `packaging/` 目录：
- libccd-2.1-ohos-aarch64.tar.gz (123KB)
- libccd-2.1-ohos-aarch64-debug.tar.gz (27KB)