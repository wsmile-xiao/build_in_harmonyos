# lsyncd

Lsyncd (Live Syncing Daemon) 是一个轻量级的实时同步守护进程，使用 Lua 脚本语言编写配置，监控文件系统事件（如 inotify 或 fsevents），并执行相应的同步操作（如 rsync）。

## 描述

lsyncd 是一个同步工具，能够：
- 实时监控本地目录变化
- 通过 rsync/rsyncssh 将变化同步到远程服务器
- 支持多种同步模式和自定义配置
- 使用 Lua 语言编写灵活的配置文件

## 编译版本

- **版本**: 2.3.1
- **构建系统**: CMake
- **编译日期**: 2026-06-04

## 编译依赖

- lua/5.3.6

## 编译配置

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DWITH_INOTIFY=ON \
  -DLUA_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include \
  -DLUA_LIBRARIES=/storage/Users/currentUser/usr/local/lib/liblua.a \
  -DCMAKE_INSTALL_MANDIR=share/man
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 补丁说明

### 0001-CMakeLists.txt.patch

**问题**: lsyncd 编译时，Lua 头文件目录中的 `config.h`（来自 libunistring）被错误地优先找到，导致编译失败。

**修复**: 调整 CMakeLists.txt 中 `include_directories` 的顺序，确保 build 目录（包含正确的 config.h）在 Lua 头文件目录之前。

**关键修改**:
- 将 `configure_file` 和 `include_directories("${PROJECT_BINARY_DIR}")` 移到 Lua `include_directories` 之前
- 确保包含路径顺序：build 目录优先，然后是 Lua 头文件目录

## 运行验证

```bash
$ lsyncd --version
Version: 2.3.1
```

## 预编译包

- `lsyncd-2.3.1-ohos-aarch64.tar.gz` (477KB)
- `lsyncd-2.3.1-ohos-aarch64-debug.tar.gz` (70KB)