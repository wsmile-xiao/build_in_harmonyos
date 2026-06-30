# libtracefs 1.8.3 编译记录

## 编译日期
2026-06-12

## 编译环境
- OS: OHOS SDK 26.0.0.18
- Compiler: clang 15.0.4
- 构建系统: makefile

## 依赖
- libtraceevent 1.9.0

## 编译过程

### 1. 源码获取
从 GitHub mirror 克隆: https://github.com/rostedt/libtracefs.git

### 2. 编译错误与解决

#### 错误1: OHOS SDK header conflict
**现象**: 编译 tracefs-vsock.c 时出现 sockaddr_storage 重复定义错误
```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
struct sockaddr_storage {
       ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
```

**原因**: OHOS SDK 中 `linux/vm_sockets.h` 包含了 `linux/socket.h`,而 `sys/socket.h` 也定义了相同的结构体 `sockaddr_storage`，导致冲突。

**解决方案**: 创建补丁文件，在 tracefs-vsock.c 中定义本地 vm_sockets 类型，避免包含 `linux/vm_sockets.h`。

### 3. 补丁文件
- `0001-src-tracefs-vsock.c-ohos-header-conflict.patch`: 定义本地 sockaddr_vm 结构体，避免 OHOS SDK 头文件冲突

### 4. 编译命令
```bash
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$HOME/usr/local/lib64:$LD_LIBRARY_PATH"
export CC="clang"
export AR="llvm-ar"
export CFLAGS="-I$HOME/usr/local/include/traceevent -I$HOME/usr/local/include"
export LDFLAGS="-L$HOME/usr/local/lib64 -L$HOME/usr/local/lib"
make
```

### 5. 安装
手动安装到 DESTDIR 目录

## 产物
- libtracefs.so.1.8.3 (动态库)
- libtracefs.a (静态库)
- tracefs.h (头文件)
- libtracefs.pc (pkg-config 文件)

## 知识提取
- OHOS SDK 存在 sys/socket.h 和 linux/socket.h 的结构体重复定义问题
- 解决方案: 定义本地类型替代包含冲突头文件
- 此问题可能影响其他使用 linux/vm_sockets.h 或类似 linux socket 头文件的软件

## 测试
未执行 make test（需要 root 权限访问 /sys/kernel/tracing）
---

**编译结束**: 2026-06-12 16:54
**最终状态**: built
