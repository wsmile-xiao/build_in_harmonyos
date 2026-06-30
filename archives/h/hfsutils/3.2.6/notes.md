# hfsutils 3.2.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码包（从 Fedora 项目镜像获取，原始 Savannah 和 OSUOSL URL 不可用）
2. `./configure --prefix=$DEFAULT_PREFIX`
3. `make -j1`（编译成功，符号链接替代硬链接）
4. `make install DESTDIR=$TEST_PREFIX`（使用 DESTDIR 模式安装到 staging）
5. `make install`（部署到本地）
6. 验证命令可用（hmount/hls/hvol 等正常执行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败（SSL证书验证失败/404） | Savannah和OSUOSL镜像不可用 | 使用 Fedora 项目镜像 URL：https://src.fedoraproject.org/repo/pkgs/hfsutils/hfsutils-3.2.6.tar.gz/fa572afd6da969e25c1455f728750ec4/hfsutils-3.2.6.tar.gz |
| 2 | 二进制执行 SIGSYS (exit code 159) | `setreuid()` 是鸿蒙未实现的 syscall (E051) | 在 suid.c 中添加 `#ifdef __OHOS__` 守卫，使用 `setuid/setgid` 替代 `setreuid/setregid` (R8) |
| 3 | HMDFS 不支持硬链接 | `ln -f` 在 HMDFS 文件系统上失败 | 修改 Makefile.in：HARDLINK=ln -s，CLITARGETS规则改为 rm -f && ln -s（§7 Gotchas） |
| 4 | make install 删除 hfsutil 后符号链接失效 | 原始 Makefile 安装后删除 hfsutil 二进制 | 注释掉 `rm -f "$(BINDEST)/$(HFSUTIL)"`，保留 hfsutil 作为符号链接目标 |
| 5 | Makefile 不支持 DESTDIR | 原始 Makefile 使用绝对路径安装 | 添加 DESTDIR 变量并在所有安装路径前加 $(DESTDIR) 前缀，添加 mkdir -p 创建目录 (R20) |
| 6 | G4 门禁失败 | manifest.yaml 缺少 `build_system` 顶级字段 | 添加 `build_system: autotools` 到 manifest.yaml |

## 源码修改（2个补丁）

### 0001-Makefile.in.patch
- HARDLINK: `ln -f` → `ln -s`（HMDFS 不支持硬链接）
- CLITARGETS 规则: `-$(HARDLINK)` → `rm -f && $(HARDLINK)`（先删除再创建符号链接）
- 注释掉 `rm -f "$(BINDEST)/$(HFSUTIL)"`（保留符号链接目标）
- 添加 DESTDIR 变量和 $(DESTDIR) 前缀到所有安装路径
- 添加 `mkdir -p` 创建 DESTDIR 目标目录

### 0002-suid.c.patch
- suid_enable(): `#ifdef __OHOS__` 守卫 → `setuid(euid); setgid(egid);` 替代 `setreuid/setregid`
- suid_disable(): `#ifdef __OHOS__` 守卫 → `setuid(uid); setgid(gid);` 替代 `setreuid/setregid`

## 依赖版本

- 无外部依赖（required=[], optional=[]）

## 验证结果

```bash
$ hmount
hfsutils version 3.2.6 - Copyright (C) 1996-1998 Robert Leslie

$ hls
hls: No volume is current; use `hmount' or `hvol'

$ hvol
No known volumes; use `hmount' to introduce new volumes

$ hattrib
Usage: hattrib [-t TYPE] [-c CREA] [-|+i] [-|+l] hfs-path [...]
```

所有命令正常执行（无 SIGSYS 错误）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hfsutils-3.2.6-ohos-aarch64.tar.gz | 2430KB | 预编译包 |

## 质量门禁

| 门禁 | 结果 |
|------|------|
| G0 (干净构建验证) | PASS |
| G1 (二进制完整性) | PASS |
| G2 (功能可用性) | PASS |
| G3 (可移植性) | PASS |
| G4 (档案完整性) | PASS |

## 注意事项

1. hfsutils 使用"单二进制多命令名"模式（类似 busybox），通过 argv[0] 区分命令行为
2. 原始 Makefile 使用硬链接+删除原始文件名的方式安装，在 HMDFS 上需要改为保留原始文件+符号链接
3. `make check` 无可用自测试（需要 `--with-tcl` 配置）
4. `setreuid` 是鸿蒙未实现 syscall，需用 `#ifdef __OHOS__` 守卫替代
5. 原始 Makefile 不支持 DESTDIR，需要手动添加 $(DESTDIR) 前缀

---
**编译结束**: 2026-06-04
**最终状态**: published
---

**编译结束**: 2026-06-04 12:43
**最终状态**: published
