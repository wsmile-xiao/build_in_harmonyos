# stress-ng

stress-ng will stress test a computer system in various selectable ways.

## 项目信息

- **官方仓库**: https://github.com/ColinIanKing/stress-ng
- **编译版本**: 0.21.01
- **编译系统**: Makefile
- **编译器**: clang 15.0.4
- **目标平台**: aarch64-linux-ohos (OpenHarmony)

## 功能概述

stress-ng 是一个强大的系统压力测试工具，包含超过 300 个压力测试项，涵盖：
- CPU、内存、I/O 压力测试
- 文件系统、网络压力测试
- 进程调度、信号处理测试
- 各种系统调用测试

## OpenHarmony 平台适配

### 主要适配问题

1. **E091: sockaddr_storage/sysinfo 重定义冲突**
   - OpenHarmony 内核头文件 `linux/socket.h` 和 `linux/sysinfo.h` 与 musl libc 结构体冲突
   - 影响 10+ 源文件，需要在 include 前重命名结构体

2. **E103: __packed 重复符号错误**
   - OHOS 内核头文件将 `__packed` 定义为变量而非宏
   - 影响 stress-binderfs.c、stress-userfaultfd.c、stress-syscall.c
   - 需要在 include 前重定义为宏

3. **Makefile PREFIX 适配**
   - 修改安装路径为 PREFIX 变量

### 编译补丁

- `0001-Makefile.patch` - PREFIX 路径适配
- `0001-stress-af-alg.c.patch` 等 10 个源文件补丁 - 头文件冲突修复

## 编译命令

```bash
make CC=clang PREFIX=/usr/local
make install DESTDIR=/path/to/staging
```

## 版本索引

| 版本 | 状态 | 发布日期 |
|------|------|----------|
| 0.21.01 | built | 2026-05-26 |