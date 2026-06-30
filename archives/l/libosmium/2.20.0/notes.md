# libosmium 2.20.0 适配笔记

## 编译环境

- **系统**: HarmonyOS (OpenHarmony)
- **编译器**: clang 15.0.4
- **构建系统**: cmake
- **日期**: 2026-05-21

## 编译步骤

1. 使用 git clone 获取源码（HTTPS 下载 SSL 证书问题）
2. 修改 CMakeLists.txt 的 cmake_minimum_required VERSION 2.8.12 为 3.5
3. 禁用可选依赖: `-DOsmium_COMPONENTS=""`
4. 运行 cmake 配置
5. 安装头文件到 ~/usr/local/include/osmium/

## 问题与方案

### 问题1: CMake 版本兼容性
- **原因**: cmake_minimum_required VERSION 2.8.12 不兼容 CMake 4.1.2
- **解决方案**: 修改为 VERSION 3.5

### 问题2: HTTPS 下载失败
- **原因**: SSL 证书验证问题
- **解决方案**: 使用 git clone 替代 HTTPS 下载

### 问题3: 缺少可选依赖
- **原因**: Protozero, LZ4, GDAL 等未安装
- **解决方案**: 禁用 find_package(Osmium COMPONENTS)

## 交付物

- 头文件: osmium/*.h (198 个文件)
- 预编译包: libosmium-2.20.0-ohos-aarch64.tar.gz (1.8MB)

## 验证

```cpp
#include <osmium/osm/location.hpp>
// 编译测试成功
```