# libtracefs

## 简介

libtracefs是Linux trace filesystem的API库，提供访问和操作tracefs文件系统的接口，是Linux tracing系统的核心组件之一。

## OHOS 适配

**适配要点**：
- 纯Makefile项目，无configure脚本
- 依赖libtraceevent
- 需补丁解决OHOS SDK vsock头文件冲突

**已知问题**：
- OHOS SDK linux/vm_sockets.h和sys/socket.h都定义sockaddr_storage导致重复定义（需补丁）
- 测试需要root权限访问/sys/kernel/tracing（可跳过）

**补丁说明**：
- `0001-src-tracefs-vsock.c-ohos-header-conflict.patch`：定义本地vm_sockets类型避免头文件冲突

## 依赖

**编译依赖**：
- libtraceevent 1.9.0

**运行依赖**：
- libtraceevent.so.1

## 功能验证

```bash
# 库验证
pkg-config --modversion libtracefs
# 应返回: 1.8.3

# 查看依赖
ldd /storage/Users/currentUser/usr/local/lib/libtracefs.so
# 应显示依赖libtraceevent.so.1和libc.so
```

## 产物

- **动态库**: libtracefs.so.1.8.3
- **静态库**: libtracefs.a
- **头文件**: tracefs.h
- **pkg-config**: libtracefs.pc

## 参考

- 官方仓库: https://git.kernel.org/pub/scm/libs/libtrace/libtracefs.git/
- Linux tracing文档: https://www.kernel.org/doc/html/latest/trace/