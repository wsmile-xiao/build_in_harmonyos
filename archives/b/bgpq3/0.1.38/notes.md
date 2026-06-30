# bgpq3 0.1.38 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 目标平台: OpenHarmony / aarch64 (musl libc)
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub releases 获取 v0.1.38 tarball
2. **configure**: 执行 `./configure`，自动检测系统特性（musl libc 提供 strlcpy、sys/queue.h 含 STAILQ 等）
3. **make**: 直接 `make` 编译，无特殊选项，生成 bgpq3 二进制
4. **make install DESTDIR**: 安装到 staging 目录用于打包
5. **make install**: 正式安装到 ~/usr/local/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 创建临时目录失败 | HMDFS 文件系统不支持 `mktemp -d "./confXXXXXX"` 在当前目录创建随机临时目录 | 修改 configure 脚本，将临时目录创建改为 `mkdir -p "${TMPDIR:-/tmp}/cs_tmp"` |
| 2 | make install 无法支持 DESTDIR | 原始 Makefile.in 未使用 DESTDIR 变量，且 install 命令含 `-s` strip 选项（与打包流程冲突） | 重写 Makefile.in install 目标，添加 `$(DESTDIR)` 前缀，移除 `-s` strip 选项 |
| 3 | Makefile.in 含行尾多余空格 | 无功能影响，但影响补丁纯净度 | 清理行尾空格 |

## 源码修改

### 0001-Makefile.in.patch
- 修改 install 目标，添加 DESTDIR 支持使 `make install DESTDIR=xxx` 正常工作
- 移除 install 命令中的 `-s`（strip）选项，由 ohc 打包流程统一处理
- 清理行尾空格

### 0002-configure.patch
- 修改 configure 脚本中临时目录创建逻辑：将 `mktemp -d "./confXXXXXX"` 替换为 `mkdir -p "${TMPDIR:-/tmp}/cs_tmp"`
- 适配 HMDFS 文件系统限制（无法在当前目录创建随机临时文件）

## 依赖版本

- musl libc（系统自带）
- clang（系统自带 / /data/service/hnp/bin/clang）
- 无第三方库依赖

## 验证结果

```bash
$ ~/usr/local/bin/bgpq3 2>&1 | grep version
bgpq3 version: 0.1.38
Copyright(c) Alexandre Snarskii <snar@snar.spb.ru> 2007-2025

$ file ~/usr/local/bin/bgpq3
~/usr/local/bin/bgpq3: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d ~/usr/local/bin/bgpq3 | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bgpq3-0.1.38-ohos-aarch64.tar.gz | 165KB | 主预编译包（含 bin/bgpq3、man8/bgpq3.8） |
| bgpq3-0.1.38-ohos-aarch64-debug.tar.gz | 140KB | 调试符号包 |

## 注意事项

- bgpq3 不支持 `--version` 或 `-V` 专用参数，版本信息在 usage 输出末尾显示
- bgpq3 仅依赖 libc.so（musl），是轻量级网络工具
- 核心功能依赖外部 IRRD 服务器（whois.radb.net），离线环境无法执行完整查询功能测试
---

**编译结束**: 2026-06-13 15:08
**最终状态**: published
