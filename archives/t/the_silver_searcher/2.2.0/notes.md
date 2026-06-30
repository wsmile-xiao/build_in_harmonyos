# the_silver_searcher 2.2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码（GitHub releases，官方 Savannah tarball 404）
2. 编译安装依赖 pcre 8.45（libpcre，而非 libpcre2）
3. autoreconf -i 生成 configure（因 automake 版本问题）
4. ./configure --prefix=$DEFAULT_PREFIX --disable-lzma（缺少 liblzma）
5. make CFLAGS="-fcommon ..."（解决 duplicate symbol 问题）
6. make install DESTDIR=$TEST_PREFIX（staging 安装）
7. make install（最终安装）
8. 验证：ag --version 输出正确

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah tarball 404 | 镜像服务器问题 | 改用 GitHub releases: https://github.com/ggreer/the_silver_searcher/archive/refs/tags/2.2.0.tar.gz |
| 2 | SSL证书验证失败 | HMDFS SSL限制 | curl -k -L 下载 |
| 3 | 缺少 libpcre | 未安装 pcre1（已安装 pcre2） | 手动编译安装 pcre 8.45 |
| 4 | autogen.sh失败 | automake 1.17与实际1.16版本不匹配 | 使用系统 autoreconf -i，手动添加 pkg.m4 |
| 5 | configure umask权限问题（E011） | HMDFS umask 077导致Permission denied | 修改 configure 中 umask 077 → umask 022（**E011 平台适配，无需补丁固化**） |
| 6 | PKG_CHECK_MODULES未展开 | 缺少 pkg.m4 | 手动添加到 aclocal.m4 |
| 7 | 缺少 liblzma | 未安装 lzma | 禁用 --disable-lzma |
| 8 | zfile.c 条件编译错误 | 源码 bug：HAVE_LZMA_H保护范围错误导致缩进混乱 | 修复缩进和条件编译结构 |
| 9 | duplicate symbol (print_mtx/opts) | 头文件全局变量重复定义 | 使用 -fcommon 标志 |

## 源码修改

- **0001-src-zfile.c.patch**: 修复 HAVE_LZMA_H 条件编译结构
  - 修复 union 中 lzma_stream 的条件编译
  - 修复 lzret 变量声明和初始化的条件编译
  - 修复 else 分支的 lzma_code 调用的条件编译
  - **注意**: 原始源码缩进有严重 bug（第 228-275 行），已修复

## 平台适配修改（无需补丁固化）

根据 **R21（Phase 3 结束必须自检零介入）** 和 **E011（HMDFS umask 077 权限问题）**：

- **configure 脚本修改**（E011 平台适配，无需补丁）：
  - 修改位置：configure 脚本中的 `umask 077`
  - 修改为：`umask 022`
  - 原因：HMDFS 文件系统的 UID 映射机制导致 umask 077 创建的临时目录无法被当前进程写入
  - 参考：knowledge/graph/E011.kv（rec_approach: edit-umask-in-configure）
  - **固化方式**：每次 configure 前执行 `sed -i 's/umask 077/umask 022/g' configure`

**其他平台适配说明**：
- autoreconf -i：因 automake 版本不匹配，需重新生成 configure
- 手动添加 pkg.m4：系统缺少 PKG_CHECK_MODULES 宏定义

## 依赖版本

- pcre 8.45 (libpcre，非 pcre2)
- zlib (系统自带)
- clang 15.0.4

## 验证结果

```bash
$ ~/usr/local/bin/ag --version
ag version 2.2.0

Features:
  +jit -lzma +zlib

$ ~/usr/local/bin/ag --help | head -5
Usage: ag [FILE-TYPE] [OPTIONS] PATTERN [PATH]
  Recursively search for PATTERN in PATH.
  Like grep or ack, but faster.
```

## 交付物

编译成功，预编译包已生成：
- 二进制文件: ag (260KB)
- 补丁: 0001-src-zfile.c.patch (5.5KB)
- 预编译包: the_silver_searcher-2.2.0-ohos-aarch64.tar.gz (332KB)

## 注意事项

1. **源码严重 bug**: zfile.c 第 226-275 行的缩进和条件编译结构完全错误，原始源码无法在没有 liblzma 的情况下编译
2. **make check**: 无测试套件（Nothing to be done for 'check'）
3. **压缩文件搜索**: 因禁用 HAVE_FOPENCOOKIE（zfile.c未编译）和 lzma，不支持 xz/lzma 压缩文件搜索，但支持 zlib (gzip)
4. **G0 干净构建验证限制**: 原始源码缺少 configure 脚本，需要 autoreconf -i 生成。当前 clean_verify 不支持此场景，已记录为平台特殊处理（参考 E011）
---

**编译结束**: 2026-05-25 21:04
**最终状态**: built
