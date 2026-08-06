# fprobe-ulog 1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/opoplawski/fprobe-ulog/releases/download/v1.2/fprobe-ulog-1.2.tar.gz
2. 下载内联依赖源码:
   - libmnl 1.0.5: https://ftp.netfilter.org/pub/libmnl/libmnl-1.0.5.tar.bz2
   - libnetfilter_log 1.0.2: https://ftp.netfilter.org/pub/libnetfilter_log/libnetfilter_log-1.0.2.tar.bz2
3. 从 conan 仓库获取 libnfnetlink/1.0.2
4. 修复 config.guess/config.sub (HarmonyOS → aarch64-unknown-linux-gnu)
5. 修复 configure umask 077→022 (HMDFS 兼容)
6. 创建 compat_fixup.h (头文件冲突解决)
7. 修复 libnfnetlink linux_nfnetlink.h 头文件冲突
8. 构建 libmnl → 构建 libnetfilter_log → 构建 fprobe-ulog
9. 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2004 年版本的 config.guess 不支持 HarmonyOS | 替换为输出 aarch64-unknown-linux-gnu 的简单脚本 |
| 2 | config.status 无法创建临时文件 | HMDFS 上 umask 077 创建的目录无法写入文件 | 将 configure/config.status 中的 umask 077 改为 umask 022 |
| 3 | sockaddr_storage 重定义 | OHOS SDK 的 linux/socket.h 和 sys/socket.h 都定义此结构 | 创建 compat_fixup.h，include sys/socket.h 后 define _UAPI_LINUX_SOCKET_H 阻止 linux/socket.h 加载 |
| 4 | __kernel_sa_family_t 未定义 | 阻止 linux/socket.h 后丢失此类型定义 | 在 compat_fixup.h 中 typedef unsigned short __kernel_sa_family_t |
| 5 | nfgenmsg 重定义 | libnfnetlink 自带 linux_nfnetlink.h 与 OHOS SDK 的 linux/netfilter/nfnetlink.h 冲突 | 将 libnfnetlink 的 linux_nfnetlink.h 替换为 forward 到系统头文件 |
| 6 | libmnl 和 libnetfilter_log 不在 conan 仓库 | 这两个包尚未适配发布 | 在 conanfile.py build() 中从源码内联构建 |

## 依赖版本
- libnfnetlink/1.0.2 (from conan repo)
- libmnl/1.0.5 (built from source)
- libnetfilter_log/1.0.2 (built from source)
- pthread (system library)

## 验证结果

```bash
$ fprobe-ulog -h
fprobe-ulog: a NetFlow probe. Version 1.2
Usage: fprobe-ulog [options] remote:port[/[local][/type]] ...
...
```

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/fprobe-ulog | NetFlow probe binary |
| lib/libnetfilter_log_libipulog.so | Inline dependency library |
| lib/libnetfilter_log.so | Inline dependency library |
| lib/libmnl.so | Inline dependency library |
---

**编译结束**: 2026-08-06 12:34
**最终状态**: published
