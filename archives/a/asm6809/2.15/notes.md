# asm6809 2.15 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac, Makefile.am, autogen.sh)
- 编译日期: 2026-08-24
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

1. **autoreconf -fi**: 源码是 git snapshot，无预生成 configure，需要 autoreconf 生成
2. **CC wrapper**: 创建 cc-wrapper.sh 包装 clang，添加 `-fuse-ld=/data/service/hnp/bin/ld`（使用 GNU ld 替代有缺陷的 OHOS SDK lld），编译后用 binary-sign-tool 签名输出二进制（E077）
3. **构建位置**: 在 tmpfs (/data/storage/el2/base) 上构建，避免 HMDFS umask 077 导致 config.status 无法创建临时文件（E011/E002）
4. **./configure --prefix=$PREFIX**: 原生编译，不用 --host/--build/--target
5. **make -j1**: 编译成功
6. **make install**: 安装到 DESTDIR
7. **make check**: 3/3 测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 错误提取 doc/ 子目录为源码 | 嵌套源码检测误判 | 手动重新提取完整 tarball |
| 2 | C compiler cannot create executables | OHOS SDK lld 缺少 libxml2.so.16 依赖 | -fuse-ld=/data/service/hnp/bin/ld 使用 GNU ld |
| 3 | cannot run C compiled programs | OHOS 需要签名才能执行 ELF | CC wrapper 自动签名 conftest 二进制 (E077) |
| 4 | config.status: Permission denied | HMDFS umask 077 (E011) | 在 tmpfs (/data/storage/el2/base) 上构建 |
| 5 | 安装后二进制 Operation not permitted | install -c 可能损坏签名 | make install 后重新签名 (E077 四步流程) |

## 验证结果

```
$ asm6809 --version
asm6809 2.15
Copyright (C) 2025 Ciaran Anscomb
License: GNU GPL version 3 or later <http://www.gnu.org/licenses/gpl-3.0.html>.

$ make check
PASS: test-isa6809.sh
PASS: test-isa6309.sh
PASS: test-pseudo.sh
============================================================================
Testsuite summary for asm6809 2.15
============================================================================
# TOTAL: 3
# PASS:  3
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```

## 依赖版本

无外部依赖。gnulib 已包含在源码中。

## 注意事项

- 源码 tarball 是 GitHub tarball，URL 不以 .tar.gz 结尾，conandata.yml 需要指定 filename
- 需要在 OHOS 上签名才能执行（E077），conanfile.py 中 CC wrapper 自动处理
- HMDFS 文件系统的 umask 077 问题需要在 tmpfs 上构建（E011）
---

**编译结束**: 2026-08-24 16:22
**最终状态**: built
