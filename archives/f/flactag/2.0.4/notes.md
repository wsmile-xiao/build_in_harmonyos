# flactag 2.0.4 适配笔记

## 编译环境
- 构建系统: autotools (手动编译因 HMDFS 临时文件限制)
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. init-build 初始化环境
2. 应用 config.guess/config.sub 补丁（支持 HarmonyOS）
3. configure 成功但 config.status 失败（HMDFS 临时文件限制）
4. 手动从 config.log 提取配置创建 config.h
5. 手动编译所有源文件（21 个 C++ 文件）
6. 手动链接生成 flactag 和 discid
7. 安装到 staging 和系统路径

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 缺少 slang/libmusicbrainz5 | pkg-config 找不到库 | 创建 slang.pc 和 libmusicbrainz5.pc 文件 |
| 2 | config.status 失败 | HMDFS 不支持当前目录创建临时文件 | 手动从 config.log 提取 #define 创建 config.h |
| 3 | slang 缺少 terminfo 符号 | sltermin.o 未编译入 libslang.a | 编译 sltermin.c 并添加到 libslang.a |
| 4 | SSL 符号未定义 | libmusicbrainz5cc 需要 OpenSSL 3.x | 链接时使用 OpenSSL 3.x 库（libssl.so.3/libcrypto.so.3） |

## 源码修改

### build-aux/config.guess
- 第 136 行：添加 HarmonyOS 到系统列表
- 第 908-910 行后：添加 aarch64:HarmonyOS 分支

### build-aux/config.sub
- 第 117-118 行：添加 linux-ohos* 到 maybe_os
- 第 125-128 行后：添加 ohos-linux 分支
- 第 1376 行：添加 -ohos* 到 OS 白名单
- 第 1396 行：添加 -linux-ohos* 到 kernel-os 白名单

## 依赖版本

- libdiscid: 0.6.5 (预编译包)
- neon: 0.35.0 (预编译包)
- flac/FLAC++: 1.4.3 (预编译包)
- libjpeg: 系统库
- slang: 2.3.3 (本地编译静态库)
- libmusicbrainz5cc: 5.1.0 (本地编译)
- unac: 1.7.0 (本地编译)
- OpenSSL: 3.x (external)

## 验证结果

```bash
# 版本验证
~/usr/local/bin/flactag --version
# 输出: flactag: Version 2.0.4

# discid 测试
~/usr/local/bin/discid
# 输出: Usage: ~/usr/local/bin/discid pathtocddevice

# 功能测试
~/usr/local/bin/flactag --help
# 输出: Usage: ~/usr/local/bin/flactag [ --version | -v ] [ --submit-url | -s ] ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| flactag | 1.0M | 主程序（带 SSL 依赖） |
| discid | 135K | 辅助程序（discid 查询） |
| flactag.1 | 12K | man 文档 |

## 注意事项

- flactag 依赖 OpenSSL 3.x（在 ~/usr/local/lib/external）
- 运行时需要设置 LD_LIBRARY_PATH 包含 OpenSSL 3.x 路径
- slang 使用静态库（libslang.a）
- discid 功能受平台限制（光盘读取未实现）
---

**编译结束**: 2026-06-16 11:35
**最终状态**: built
