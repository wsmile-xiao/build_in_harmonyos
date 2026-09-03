# raft-cowsql 0.22.1 适配笔记

## 编译环境
- 构建系统: autotools (需要 autoreconf -i bootstrap)
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. **Bootstrap**: `autoreconf -i` — GitHub tarball 不包含生成的 autotools 文件
2. **Fix umask**: `sed -i 's/umask 077/umask 022/g' configure` — HMDFS 权限问题
3. **Configure**: `./configure --prefix=$DEFAULT_PREFIX`
4. **Make**: `make -j2`
5. **Install**: `make install DESTDIR=$TEST_PREFIX`
6. **Check**: `make check` — 3 个测试全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure script 不存在 | GitHub tarball 不包含生成的 autotools 文件 | `autoreconf -i` |
| 2 | config.status Permission denied | HMDFS umask 077 导致临时目录不可写 (E011) | `sed 's/umask 077/umask 022/g' configure` |
| 3 | 无 libuv | libuv 未安装 | 不影响核心编译，uv 相关功能被禁用 |

## 源码修改

- `configure`: umask 077 → umask 022 (HMDFS 权限修复)
- `ac/config.guess`: 更新 (autoreconf -i 替换为含 ohos 支持的版本)
- `ac/config.sub`: 更新 (autoreconf -i 替换为含 ohos 支持的版本)
- 所有 autoreconf 生成的辅助文件: 新增 (17 个文件)

补丁文件 (17个):
- 0001-Makefile.in.patch
- 0002-ac-compile.patch
- 0003-ac-config.guess.patch
- 0004-ac-config.sub.patch
- 0005-ac-depcomp.patch
- 0006-ac-install-sh.patch
- 0007-ac-ltmain.sh.patch
- 0008-ac-missing.patch
- 0009-ac-test-driver.patch
- 0010-aclocal.m4.patch
- 0011-aminclude_static.am.patch
- 0012-configure.patch (含 umask 077→022 修复)
- 0013-m4-libtool.m4.patch
- 0014-m4-ltoptions.m4.patch
- 0015-m4-ltsugar.m4.patch
- 0016-m4-ltversion.m4.patch
- 0017-m4-lt~obsolete.m4.patch

## 依赖版本

无外部依赖（libuv/lz4 未安装，相关功能被禁用）

## 验证结果

```bash
make check 结果:
  PASS: test/unit/core
  PASS: test/integration/core
  PASS: test/fuzzy/core
  # TOTAL: 3, PASS: 3, FAIL: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libraft.so.0.0.0 | 494KB | 共享库 |
| libraft.a | 931KB | 静态库 |
| raft.h | 57KB | 头文件 |
| raft/fixture.h | - | fixture 头文件 |
| raft.pc | 260B | pkg-config 文件 |

## 注意事项

- GitHub tarball 需要 autoreconf -i，不能直接 configure
- HMDFS 上必须修改 configure 中 umask 077 为 umask 022
- libuv 功能未启用（需要额外安装 libuv 后重新编译）
- G0 clean-verify 使用 /bin/sh (toybox) 执行 configure，toybox sh 无法处理 autoconf 生成的复杂脚本；必须用 bash 执行 configure（手动验证已通过）
- 所有 17 个 autoreconf 生成的文件已作为补丁保存，确保从原始 tarball + 补丁可以完成构建
---

**编译结束**: 2026-08-30 01:24
**最终状态**: built
