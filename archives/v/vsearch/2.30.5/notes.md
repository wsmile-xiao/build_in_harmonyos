# vsearch 2.30.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**: 从 GitHub 下载 vsearch v2.30.5 tarball
2. **运行 autogen.sh**: 生成 configure 脚本（需要设置 AUTOCONF 环境变量）
3. **手动复制 automake 辅助文件**: config.guess, config.sub, install-sh, depcomp, compile, missing
4. **运行 configure**: `./configure --prefix=$DEFAULT_PREFIX`
5. **运行 make**: `make -j2`
6. **运行 make install**: `make install DESTDIR=$TEST_PREFIX`（staging 安装）
7. **验证二进制**: `vsearch --version` 确认可执行
8. **打包**: `ohc-run.py package vsearch 2.30.5`
9. **本地安装**: `make install`（不带 DESTDIR）
10. **归档**: `ohc-run.py finish vsearch 2.30.5 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 (504) | 网络问题 | 使用 curl 手动下载，复制到 tarballs 目录 |
| 2 | autoreconf 失败，autoconf inaccessible | 本地 autoconf 符号链接指向 /data/service/hnp，automake 使用错误路径 | 设置 `AUTOCONF=/data/service/hnp/autoconf.org/autoconf_2.72/bin/autoconf` |
| 3 | automake 复制辅助文件失败 (cp Permission denied) | toybox cp 权限问题，Perl 无法执行外部命令 | 手动从 automake 数据目录复制辅助文件 |
| 4 | G4 检查失败，manifest 缺少 build_system | 脚本检查顶层字段 | 在 manifest.yaml 添加顶层 `build_system: autotools` 字段 |

## 源码修改

无补丁。手动复制了 automake 辅助文件（config.guess, config.sub, install-sh, depcomp, compile, missing）。

## 依赖版本

- clang 15.0.4
- autoconf 2.72
- automake 1.17
- zlib（可选，gzip 支持）
- bzip2（可选，bzip2 支持）

## 验证结果

```bash
$ vsearch --version
vsearch v2.30.5_linux_aarch64, 31.2GB RAM, 20 cores
https://github.com/torognes/vsearch

Rognes T, Flouri T, Nichols B, Quince C, Mahe F (2016)
VSEARCH: a versatile open source tool for metagenomics
PeerJ 4:e2584 doi: 10.7717/peerj.2584

Compiled with support for gzip-compressed files, but the library was not found.
Compiled with support for bzip2-compressed files, but the library was not found.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vsearch-2.30.5-ohos-aarch64.tar.gz | 840KB | 预编译包 |
| vsearch-2.30.5-ohos-aarch64-debug.tar.gz | 133KB | 调试符号包 |

## 注意事项

- vsearch 支持 gzip 和 bzip2 压缩文件，但需要安装相应的库才能使用这些功能
- 编译时使用了 SIMD 优化（armv8-a+simd）
- 无外部库依赖，完全自包含

---
**编译结束**: 2026-06-08 16:28
**最终状态**: built
---

**编译结束**: 2026-06-08 16:31
**最终状态**: built
