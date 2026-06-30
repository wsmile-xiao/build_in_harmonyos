# ssdeep 2.14.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. 源码包下载: 从 Debian pool 获取 `ssdeep_2.14.1+git20180629.57fcfff.orig.tar.gz`
   （GitHub 和 Savannah 原始 URL 因网络限制无法直接下载）
2. 手动运行 autoreconf 生成 configure（源码包仅包含 configure.ac，无预生成 configure）
   - 需设置 AUTOM4TE=autom4te 和 AUTOCONF=autoconf 环境变量
   - 手动复制 build-aux 文件（config.guess, config.sub, ltmain.sh 等）因 HMDFS 下 libtoolize 不可用
3. `./configure --prefix=/storage/Users/currentUser/usr/local`
4. `make -j1`
5. `make install DESTDIR=~/tmp/test-install-ssdeep-2.14.1`
6. `ssdeep -V` → 2.14.1 ✅
7. `make check` → PASS ✅
8. `ohc-run.py package ssdeep 2.14.1`
9. `make install`（不带 DESTDIR，本地安装验证）
10. `/storage/Users/currentUser/usr/local/bin/ssdeep -V` → 2.14.1 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败 | GitHub/Savannah HTTPS 连接超时或 SSL 证书问题 | 从 Debian pool 下载 orig.tar.gz |
| 2 | autoreconf 失败 (libtoolize) | HMDFS 无法 readdir share/libtool/build-aux | 手动复制 build-aux 文件，手动运行 aclocal/autoconf/automake |
| 3 | aclocal 失败 (@am_AUTOM4TE@) | aclocal Perl 脚本模板未替换 | 设置 AUTOM4TE=autom4te 环境变量 |
| 4 | automake 失败 (autoconf inaccessible) | sh 无法执行 Perl 脚本（HMDFS 权限） | 设置 AUTOCONF=autoconf 环境变量 |
| 5 | automake --add-missing (cp permission) | Perl 脚本内 `cp` 命令 HMDFS 不可用 | 手动复制 build-aux 文件后跳过 --add-missing |
| 6 | ssdeep --version 不生效 | ssdeep 使用 `-V` 而非 `--version` | 使用 `ssdeep -V` 验证版本 |
| 7 | verify-build G4 FAIL | manifest.yaml 缺少 top-level `build_system` 字段 | 手动添加 `build_system: autotools` |
| 8 | verify-build "无二进制文件" | DESTDIR 模式下文件在 $TEST_PREFIX/$DEFAULT_PREFIX/ 下 | 使用 `--install-prefix` 指定正确路径 |

## 源码修改

无补丁。源码包来自 Debian orig tarball（ssdeep_2.14.1+git20180629.57fcfff.orig.tar.gz），
需要手动运行 autotools 生成 configure 和 Makefile.in。

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- automake 1.16.5
- libtool 2.4.7
- GNU sed（预编译包）

## 验证结果

```bash
$ ssdeep -V
2.14.1
$ ssdeep -h
ssdeep version 2.14.1 by Jesse Kornblum and the ssdeep Project
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ssdeep-2.14.1-ohos-aarch64.tar.gz | 370KB | 预编译包（含 ssdeep 二进制 + libfuzzy 共享库 + 头文件 + man 页） |
| ssdeep-2.14.1-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

1. ssdeep 版本验证使用 `-V` 参数（不是 `--version`）
2. 源码包需要手动 bootstrap（autoreconf），不能直接 ./configure
3. 在 HMDFS 环境下 libtoolize 和 automake 的 --add-missing 功能受限，需要手动复制辅助文件
4. aclocal 和 automake 需要设置 AUTOM4TE/AUTOCONF 环境变量才能正常工作
5. DESTDIR 模式下 verify-build 需要使用 `--install-prefix` 指定 $TEST_PREFIX/$DEFAULT_PREFIX

---

**编译结束**: 2026-06-02 22:16
**最终状态**: published
---

**编译结束**: 2026-06-02 22:19
**最终状态**: published
