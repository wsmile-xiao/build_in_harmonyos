# libindi 2.1.5.1-r1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built（已编译成功）

## 依赖情况

| 依赖 | 状态 | 说明 |
|------|------|------|
| libnova/0.14.0 | ✅ 已安装 | 需手动创建 pkg-config 文件 |
| cfitsio/4.6.4 | ✅ 已安装 | 预编译包 |
| zlib/1.3.1 | ✅ 已安装 | 预编译包 |
| libev/4.33 | ✅ 已安装 | 预编译包 |

## 编译记录

### 2026-06-08 编译尝试

### Step 1: 初始化
✅ 成功初始化编译环境
- 源码路径: /storage/Users/currentUser/tmp/builds/libindi-2.1.5.1-r1.work
- 构建系统: CMake

### Step 2: 配置与编译

#### 问题 1: libnova 缺少 pkg-config 文件
- **现象**: CMake 找不到 libnova
- **解决**: 手动创建 `~/usr/local/lib/pkgconfig/libnova.pc`

#### 问题 2: select.h 头文件缺失
- **现象**: `fd_set` 和 `struct timeval` 未定义
- **文件**: `libs/sockets/select.h`
- **修复**: 添加 `#include <sys/select.h>` 和 `#include <sys/time.h>`

#### 问题 3: HarmonyOS 平台识别
- **现象**: CMake 不识别 `UNIX` 变量，导致编译 tcpsocket_win.cpp
- **文件**: `libs/sockets/CMakeLists.txt`
- **修复**: 修改判断条件为 `if(CMAKE_HOST_UNIX OR UNIX OR NOT WIN32)`

### Step 3: 编译结果
✅ 编译成功
- indiserver: 已生成
- libindiclient.a: 已生成
- libindiclient.so: 已生成

## 源码修改记录

### 修改 1: libs/sockets/select.h
```patch
+#include <sys/select.h>  // fd_set, select()
+#include <sys/time.h>    // struct timeval
```

### 修改 2: libs/sockets/CMakeLists.txt
```patch
-if(UNIX)
+if(CMAKE_HOST_UNIX OR UNIX OR NOT WIN32)
```

## 知识提取

### E012: HarmonyOS CMake UNIX 变量问题
- **现象**: `if(UNIX)` 在 HarmonyOS 上返回 false
- **原因**: CMake 基于 CMAKE_SYSTEM_NAME 判断，HarmonyOS 不匹配 UNIX
- **解决**: 使用 `CMAKE_HOST_UNIX OR UNIX OR NOT WIN32`

### E013: POSIX 头文件缺失
- **现象**: `fd_set`、`select()`、`struct timeval` 未定义
- **原因**: 缺少必要的 POSIX 头文件
- **解决**: 添加 `sys/select.h` 和 `sys/time.h`

---

**编译结束**: 2026-06-08 11:30
**最终状态**: built
---

**编译结束**: 2026-06-08 11:33
**最终状态**: published
