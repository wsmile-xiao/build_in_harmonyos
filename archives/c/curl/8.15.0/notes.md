# curl 8.15.0 编译笔记

## 编译日期
2026-05-16

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang 15.0.4
- 链接器: GNU ld 2.45
- 构建系统: CMake 4.1.2

## 依赖
- OpenSSL 1.1.1w ✅
- zlib 1.3.1 ✅

## 问题与解决

### 问题1: sockaddr_storage 重复定义
**原因**: 鸿蒙 SDK 中 linux/socket.h 和 sys/socket.h 都定义了 sockaddr_storage 结构体，导致编译错误。

**解决**: 禁用 HAVE_LINUX_TCP_H，使用 netinet/tcp.h 替代。修改了以下文件：
- lib/cf-socket.c
- lib/connect.c
- lib/sendf.c
- lib/setopt.c

### 问题2: RPATH 相对路径问题
**原因**: CMake 默认使用相对路径 RPATH (`../lib/libcurl.so`)，鸿蒙系统无法正确解析。

**解决**: 使用静态链接构建 (`BUILD_SHARED_LIBS=OFF`)，避免了动态库依赖问题。

### 问题3: 编译器链接器冲突
**原因**: 默认的 lld 链接器需要 libxml2.so.16 但无法找到。

**解决**: 使用 `-fuse-ld=/data/service/hnp/binutils.org/binutils_2.45/bin/ld` 指定 GNU ld。

## 功能验证
- ✅ curl --version 输出正常
- ✅ HTTP 请求正常 (curl -I http://example.com)
- ⚠️ HTTPS 需要配置 CA 证书路径

## 补丁文件
- 0001-disable-linux-tcp-header.patch

**编译结束**: 2026-05-16 17:02
**最终状态**: built
