# libtorrent-rasterbar 2.0.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 源码解压
```bash
tar -xzf libtorrent-rasterbar-2.0.9.tar.gz
cd libtorrent-rasterbar-2.0.9
```

### 2. 创建构建目录
```bash
mkdir build && cd build
```

### 3. CMake 配置
```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DBUILD_SHARED_LIBS=ON \
  -Ddeprecated-functions=OFF
```

### 4. 编译
```bash
make -j$(nproc)
```

### 5. 安装
```bash
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_setcancelstate 等函数未定义 | musl libc 不支持完整的 pthread 取消功能 API | 创建 pthread_compat.c 兼容层，提供空实现 |
| 2 | sockaddr_storage 重定义冲突 | OHOS 在 linux/netlink.h 中定义了 sockaddr_storage，与系统定义冲突 | 在包含 netlink.h 前重定义为 __linux_sockaddr_storage，包含后恢复 |

## 源码修改

### 修改文件列表
1. **CMakeLists.txt** - 添加 pthread_compat.c 源文件
2. **include/libtorrent/netlink.hpp** - 解决 sockaddr_storage 冲突
3. **include/libtorrent/socket.hpp** - 解决 sockaddr_storage 冲突

### 补丁详情

#### 0001-CMakeLists.txt.patch
在源文件列表中添加 `pthread_compat.c`，用于提供 musl libc 缺失的 pthread 兼容函数：
```cmake
# -- OHOS pthread compat --
pthread_compat.c
```

#### 0002-include-libtorrent-netlink.hpp.patch
在包含 `<linux/netlink.h>` 前后处理 sockaddr_storage 重定义：
```cpp
#ifdef __OHOS__
#define sockaddr_storage __linux_sockaddr_storage
#endif
#include <linux/netlink.h>
#ifdef __OHOS__
#undef sockaddr_storage
#endif
```

#### 0003-include-libtorrent-socket.hpp.patch
同上，在 socket.hpp 中也应用相同的处理。

### 新增文件
- **pthread_compat.c** - pthread API 兼容层实现（需在源码目录创建）

## 依赖版本

| 软件包 | 版本 | 说明 |
|--------|------|------|
| boost | 1.84.0 | C++ 库集合，提供 ASIO 等组件 |
| openssl | 1.1.1w | SSL/TLS 加密库 |

## 验证结果

```bash
# 检查库文件
ls -lh /storage/Users/currentUser/usr/local/lib/libtorrent-rasterbar.so
# -rwxrwx--- 1 20001006 file_manager 9.1M 2026-05-26 12:01 libtorrent-rasterbar.so

# 检查头文件
find /storage/Users/currentUser/usr/local/include/libtorrent -name "*.hpp" | wc -l
# 273

# 检查依赖库
readelf -d /storage/Users/currentUser/usr/local/lib/libtorrent-rasterbar.so | grep NEEDED
# NEEDED: libssl.so.1.1
# NEEDED: libcrypto.so.1.1
# NEEDED: libc++_shared.so
# NEEDED: libc.so

# 检查 pkg-config
cat /storage/Users/currentUser/usr/local/lib/pkgconfig/libtorrent-rasterbar.pc
# Version: 2.0.9
# Libs: -L${libdir} -ltorrent-rasterbar -pthread -lssl -lcrypto

# 检查 CMake 配置
ls -lh /storage/Users/currentUser/usr/local/lib/cmake/LibtorrentRasterbar/
# LibtorrentRasterbarConfig.cmake
# LibtorrentRasterbarConfigVersion.cmake
# LibtorrentRasterbarTargets.cmake
# LibtorrentRasterbarTargets-release.cmake
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libtorrent-rasterbar.so | 9.1 MB | 动态库文件 |
| libtorrent/*.hpp | 273 files | 头文件集合 |
| libtorrent-rasterbar.pc | - | pkg-config 配置文件 |
| LibtorrentRasterbarConfig.cmake | - | CMake 配置文件 |
| LibtorrentRasterbarTargets.cmake | - | CMake 目标配置 |
| LibtorrentRasterbarTargets-release.cmake | - | CMake Release 配置 |
| LibtorrentRasterbarConfigVersion.cmake | - | CMake 版本配置 |

## 注意事项

1. **pthread 兼容性**：musl libc 不支持完整的 pthread 取消功能，如果后续版本有类似问题，可参考 pthread_compat.c 的实现方式。

2. **sockaddr_storage 冲突**：OHOS 的内核头文件与系统头文件存在类型定义冲突，使用条件编译和重定义的方式解决，不影响其他平台。

3. **CMake 配置**：
   - 必须设置 `-DCMAKE_SYSTEM_NAME=OHOS` 以正确识别平台
   - 建议关闭 deprecated-functions 选项以减少警告

4. **依赖要求**：
   - 必须使用 boost 1.84.0 或更高版本
   - 必须使用 openssl 1.1.1w 以确保 TLS 1.3 支持

5. **后续维护**：
   - 补丁已标记为 `platform_only: True`，仅适用于 OHOS 平台
   - 如需升级版本，需验证补丁是否仍然适用

---
**编译结束**: 2026-05-26 12:02
**最终状态**: built