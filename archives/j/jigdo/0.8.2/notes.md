# jigdo 0.8.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 从清华镜像下载源码: `curl -k https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/j/jigdo/jigdo_0.8.2.orig.tar.xz`
2. 安装 bzip2 依赖: 从 cmd-pkgs 下载 bzip2-1.0.8 预编译包并安装
3. 配置编译选项: `./configure --prefix=/storage/Users/currentUser/usr/local --without-libdb --without-gui`
4. 手动处理 config.status 临时目录权限问题（HMDFS限制）
5. 编译: `make -j1`（跳过文档生成）
6. 手动安装到 TEST_PREFIX 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 网络下载失败（SSL证书问题） | 鸿蒙系统 SSL 证书验证失败 | 使用 curl -k 跳过证书验证，从国内镜像下载 |
| 2 | 缺少 bzlib.h | bzip2 未安装 | 从 cmd-pkgs 下载 bzip2-1.0.8 预编译包并安装 |
| 3 | 缺少 libdb | libdb 无预编译包 | 使用 --without-libdb 禁用 db 缓存功能 |
| 4 | config.status 无法创建临时子目录 | HMDFS 文件系统限制 mktemp 创建子目录 | 手动创建临时目录并修改 config.status 使用固定目录名 |
| 5 | 文档生成失败 | 缺少 docbook2man 工具 | 跳过文档生成，只编译二进制文件 |

## 源码修改

无补丁，仅配置时禁用可选功能（libdb、GUI）。

## 依赖版本

- bzip2: 1.0.8（预编译包）
- zlib: 系统自带（configure 已检测到）
- wget: 系统自带（运行时依赖）

## 验证结果

```bash
$ jigdo-file --version
jigdo-file version 0.8.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jigdo-file | 927K | 主程序，用于生成和下载 jigdo 文件 |
| jigdo-lite | 28K | 轻量级下载脚本 |
| jigdo-mirror | 14K | 镜像管理脚本 |

## 注意事项

1. **HMDFS 临时目录限制**: config.status 使用 `mktemp -d "./confXXXXXX"` 在当前目录创建临时子目录会失败。解决方案是手动创建临时目录并修改 config.status。
2. **libdb 功能缺失**: 由于没有 libdb 的预编译包，jigdo 的 db 文件缓存功能被禁用。这不影响基本功能，但性能可能略有下降。
3. **文档缺失**: 由于缺少 docbook2man，man 页面未生成。用户可从 README 获取使用说明。

---
**编译结束**: 2026-06-11 15:39
**最终状态**: built（功能可用，未发布）
---

**编译结束**: 2026-06-11 15:42
**最终状态**: built
