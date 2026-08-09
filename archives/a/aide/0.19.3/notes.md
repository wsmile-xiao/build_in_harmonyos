# aide 0.19.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4（OHOS）
- 状态: published

## 编译步骤

1. `ohc-run.py init-build aide 0.19.3 --url=https://github.com/aide/aide/releases/download/v0.19.3/aide-0.19.3.tar.gz`
2. 给 config.guess/config.sub 打 HarmonyOS 补丁（E007，用 patch-autotools-ohos.pl）
3. 修改 configure：umask 077 → 022（HMDFS config.status 临时目录权限问题）
4. `./configure --prefix=$DEFAULT_PREFIX --with-gcrypt --with-zlib`（依赖路径经 PCRE2_CFLAGS/GCRYPT_LIBS 等注入）
5. `make -j1`（用 `ACLOCAL=/bin/true AUTOHEADER=/bin/true AUTOMAKE=/bin/true AUTOCONF=/bin/true` 绕过 aclocal-1.18 缺失）
6. `make install DESTDIR=$TEST_PREFIX`
7. `make check`（TEMP/TMPDIR 指向可写目录）→ 166 Checks 全过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess 不识 HarmonyOS（E007） | patch-autotools-ohos.pl 补 config.guess/config.sub |
| 2 | config.status: cannot create confXXXXXX/subs1.awk: Permission denied | HMDFS umask 077 临时目录不可写（E081 同类） | configure 中 umask 077 → 022 |
| 3 | aclocal-1.18: not found | make 尝试重生成 aclocal.m4，本机 automake 不完整 | make 命令行变量 ACLOCAL=/bin/true 等绕过 |
| 4 | ld.lld: unable to find library -lgcrypt | libgcrypt 仅发布 shared 包，aide 全静态链接失败 | 去掉 --enable-static，动态链接 libgcrypt |
| 5 | make check: Error loading libcheck.so.0 / Unable to create temporary file | check 库运行时 P_tmpdir=/tmp 只读 | 设置 TEMP+TMPDIR 到可写目录（$HOME/tmp） |

## 源码修改

- config.guess：__OHOS__ LIBC 检测 + HarmonyOS 系统识别分支（0001）
- config.sub：ohos-linux 三元组（0002）
- configure：umask 077 → 022（0003）

## 测试结果

- make check: 166 Checks, 0 Failures, 0 Errors（check_aide 单测套件）
---

**编译结束**: 2026-08-08 16:26
**最终状态**: published
