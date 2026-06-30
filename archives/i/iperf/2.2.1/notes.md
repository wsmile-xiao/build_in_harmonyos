# iperf 2.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 SourceForge 下载源码 tarball
2. 应用 config.guess/config.sub 补丁（OHOS 平台识别）
3. 修改 headers.h（解决 linux/socket.h 与 sys/socket.h 冲突）
4. 修改 checksums.c（适配 musl udphdr 结构体）
5. configure --prefix=$DEFAULT_PREFIX
6. make -j1
7. make install DESTDIR=$TEST_PREFIX
8. make install（安装到本地）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 补丁缺少 exit 语句 | 添加 echo "$GUESS" && exit ;; |
| 2 | config.sub 报错 "Kernel 'linux' not known to work with OS 'ohos'" | linux-ohos 组合未添加到验证列表 | 添加 linux-ohos* 到 kernel-os 验证 |
| 3 | sockaddr_storage 重复定义 | linux/tcp.h 包含 linux/socket.h 与 sys/socket.h 冲突 | 使用宏别名 #define sockaddr_storage sockaddr_storage_ohos_alias |
| 4 | udphdr.check 成员不存在 | musl libc 使用 uh_sum 命名 | 添加 #ifdef __OHOS__ 条件编译 |

## 源码修改

- config.guess: 添加 HarmonyOS 识别 + exit 语句
- config.sub: 修复 ohos-linux 格式 + 添加 linux-ohos* 验证
- include/headers.h: OHOS 头文件冲突解决方案
- src/checksums.c: musl udphdr 适配

## 依赖版本

- clang 15.0.4
- make 4.4.1
- automake 1.16.5
- autoconf 2.72

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/iperf --version
iperf version 2.2.1 (4 Nov 2024) pthreads
```

## 交付物

无预编译包（质量门禁 G0 失败）

## 注意事项

- OHOS SDK 头文件存在 linux/socket.h 与 sys/socket.h 的重复定义问题
- musl libc 的 udphdr 结构体使用 uh_sum 而不是 check
- G0 干净构建验证失败，需要进一步调试
---

**编译结束**: 2026-05-26 10:56
**最终状态**: built
