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
- **编译日期**: 2026-07-17

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

**问题**: lsyncd 编译时，Lua 源码头文件目录中的 `config.h`（Lua 自带）与 lsyncd build 目录生成的 `config.h` 同名，由于 include 顺序问题导致 Lua 的 `config.h` 被错误优先找到，引发编译冲突。

**修复**: 调整 CMakeLists.txt 中 `include_directories` 的顺序，将 `configure_file` 和 `include_directories("${PROJECT_BINARY_DIR}")` 移到 `find_package(Lua)` 之后、Lua `include_directories` 之前，确保 build 目录（包含正确的 config.h）优先于 Lua 头文件目录。

**关键修改**:
- 将 `configure_file` 和 `include_directories("${PROJECT_BINARY_DIR}")` 移到 Lua `include_directories` 之前
- 确保包含路径顺序：build 目录优先，然后是 Lua 头文件目录

### 0002-CMakeLists.txt-gnuinstalldirs.patch

**问题**: CMakeLists.txt 使用 `${CMAKE_INSTALL_MANDIR}/man1` 作为 man page 安装路径，但未包含 `include(GNUInstallDirs)`，导致 `CMAKE_INSTALL_MANDIR` 变量为空，路径变成绝对路径 `/man1`，`cmake.install()` 因无权限创建根目录而失败。

**修复**:
- 添加 `include(GNUInstallDirs)`，使 `CMAKE_INSTALL_MANDIR` 被正确设置为相对路径 `share/man`
- 移除 `prepare_tests` 自定义目标的 `ALL` 关键字，避免默认构建强制创建 `tests` 符号链接（在非管理员 Windows 环境失败，且对打包无必要；`run-tests` 目标仍可手动触发）

## 运行验证

```bash
$ lsyncd --version
Version: 2.3.1
```

## 预编译包

- `lsyncd-2.3.1-ohos-aarch64.tar.gz` (477KB)
- `lsyncd-2.3.1-ohos-aarch64-debug.tar.gz` (70KB)