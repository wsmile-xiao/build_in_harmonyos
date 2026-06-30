# libtorrent-rasterbar

## 软件描述

libtorrent-rasterbar 是一个功能完整的 BitTorrent 协议实现库，采用 C++ 编写。它提供了丰富的 API 接口，支持：

- **BitTorrent 协议**：完整实现 BitTorrent 协议规范（BEP-0003）
- **DHT 分布式哈希表**：支持无 Tracker 的去中心化节点发现
- **PEX 节点交换**：实现节点间的高效信息交换
- **uTP 传输协议**：基于 UDP 的传输协议，优化带宽使用
- **加密连接**：支持 MSE (Message Stream Encryption) 加密
- **磁力链接**：支持 magnet URI 方式获取种子
- **IPv6 支持**：完整的 IPv6 协议支持
- **高效性能**：使用 Boost.Asio 异步 I/O 模型

libtorrent-rasterbar 被广泛应用于各种 BitTorrent 客户端（如 qBittorrent、Deluge 等）以及各种基于 P2P 技术的应用程序。

**项目主页**：https://www.libtorrent.org/
**源码仓库**：https://github.com/arvidn/libtorrent

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.0.9 | ✅ built | 2026-05-26 | 支持 OpenHarmony 平台，包含必要的平台适配补丁 |

## 平台支持

- **目标平台**：OpenHarmony (OHOS)
- **架构**：aarch64
- **编译器**：clang/clang++
- **构建系统**：CMake

### 平台特性

- 动态库（共享库）支持
- 完整的头文件集合
- pkg-config 配置文件
- CMake 集成配置文件

## 依赖说明

### 必需依赖

| 依赖包 | 版本要求 | 说明 |
|--------|----------|------|
| **boost** | ≥ 1.84.0 | C++ 库集合，主要使用以下组件：<br>- Boost.Asio：异步 I/O<br>- Boost.System：系统错误码<br>- Boost.DateTime：日期时间处理<br>- Boost.Filesystem：文件系统操作（可选） |
| **openssl** | ≥ 1.1.1w | SSL/TLS 加密库，用于：<br>- 加密连接支持<br>- DHT 安全性<br>- Tracker HTTPS 连接 |

### 可选依赖

- **python**：用于 Python 绑定（可选，默认不编译）

### 运行时依赖

编译后的库依赖以下动态库：
- `libssl.so.1.1` - OpenSSL 加密库
- `libcrypto.so.1.1` - OpenSSL 加密库
- `libc++_shared.so` - LLVM C++ 运行时
- `libc.so` - C 标准库

## 使用方法

### 通过 pkg-config 使用

```bash
# 编译标志
pkg-config --cflags libtorrent-rasterbar

# 链接标志
pkg-config --libs libtorrent-rasterbar

# 示例编译命令
clang++ -o myapp myapp.cpp $(pkg-config --cflags --libs libtorrent-rasterbar)
```

### 通过 CMake 使用

```cmake
find_package(LibtorrentRasterbar REQUIRED)

target_link_libraries(myapp LibtorrentRasterbar::torrent-rasterbar)
```

### 代码示例

```cpp
#include <libtorrent/torrent.hpp>
#include <libtorrent/session.hpp>
#include <libtorrent/add_torrent_params.hpp>

int main() {
    lt::session ses;
    lt::add_torrent_params p;
    p.save_path = "/tmp";
    p.ti = std::make_shared<lt::torrent_info>("test.torrent");
    ses.add_torrent(p);

    // ... 你的代码 ...

    return 0;
}
```

## 平台适配说明

### OpenHarmony 特殊处理

1. **pthread 兼容层**
   - musl libc 不支持完整的 pthread 取消功能
   - 添加了 `pthread_compat.c` 提供兼容实现

2. **类型重定义冲突**
   - OHOS 内核头文件中定义了 `sockaddr_storage`
   - 通过条件编译和重定义方式解决冲突

详见各版本的 `notes.md` 文件获取完整的适配细节。

## 文档资源

- [官方文档](https://www.libtorrent.org/reference.html)
- [API 参考](https://www.libtorrent.org/reference.html)
- [示例代码](https://github.com/arvidn/libtorrent/tree/master/examples)

## 许可证

BSD-3-Clause License

## 相关链接

- 版本归档目录：`archives/l/libtorrent-rasterbar/`
- 预编译包目录：`prebuilt/libtorrent-rasterbar/`
- 知识库：`knowledge/graph/libtorrent-rasterbar/`