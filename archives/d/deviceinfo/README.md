# deviceinfo (lomiri-deviceinfo)

Lomiri device information library and tool for hardware detection.

## 特点

- **设备信息检测**：检测设备名称、型号、类型等硬件信息
- **C++ 库 + 工具**：提供 libdeviceinfo.so 库和 device-info 工具
- **YAML 配置**：通过 YAML 文件定义设备属性

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.2.4 | built | 2026-06-17 |

## 安装说明

deviceinfo 使用 CMake 构建：

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

安装产物：
- `lib/libdeviceinfo.so` - 共享库
- `bin/device-info` - 设备信息工具

## 使用说明

运行设备信息工具：
```bash
device-info get name
device-info get model
device-info
```

## 补丁说明

### 0001-CMakeLists.txt.patch
- 添加 RPATH 全局配置

### 0002-src-CMakeLists.txt.patch
- 添加 yaml-cpp include_directories
- 添加 libc++ 和 c++abi 链接

### 0003-tools-CMakeLists.txt.patch
- 添加 libc++ 链接和 RPATH 配置

## 源码信息

- **项目主页**: https://gitlab.com/ubports/development/core/deviceinfo
- **许可证**: LGPL-3.0

## 遇到的问题

1. **yaml-cpp 依赖**：需要安装 yaml-cpp 预编译包
2. **libc++ 链接**：musl 需显式链接 libc++ 和 c++abi
3. **RPATH 设置**：需要设置 CMAKE_INSTALL_RPATH

## 依赖

- yaml-cpp >= 0.8.0
- C++ 标准库 (libc++)