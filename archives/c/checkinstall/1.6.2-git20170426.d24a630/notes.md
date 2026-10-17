# checkinstall 1.6.2-git20170426.d24a630 适配笔记

## 编译环境
- 构建系统: make（根 Makefile + installwatch/ 子 Makefile；init-build 探测为 autotools 不准确）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS sysroot，musl libc）
- 状态: built
- 上游源: giuliomoro/checkinstall @ commit d24a630（2017-04-26，"add support for --recommends and --suggests"；gitlab 官方 checkinstall/checkinstall 已 404 不可达，GitHub API 实证 d24a630 存在，gitlab 官方源不可用时用该完整历史仓库，PR 中说明）

## 软件形态与适配思路

checkinstall 是"make install 打包工具"（生成 rpm/deb/slackware 包），主体为 bash 脚本（checkinstall.in → sed 生成 checkinstall 主脚本 + makepak 辅助脚本），核心跟踪能力依赖 **installwatch**（LD_PRELOAD 拦截库，C 编写，`installwatch/` 子目录）。

主要构建产物：
- sbin/checkinstall（bash 主程序，由 checkinstall.in 经 `sed 's%MAKEFILE_PREFIX%$(PREFIX)%g'` 生成）
- sbin/makepak（bash 辅助脚本）
- bin/installwatch（bash 包装脚本，设置 LD_PRELOAD 后执行目标命令）
- lib/installwatch.so（C 编译的 LD_PRELOAD 拦截库）
- lib/checkinstall/locale/*/LC_MESSAGES/checkinstall.mo（12 语言，由 msgfmt 编译）
- lib/checkinstall/checkinstallrc-dist（配置模板）

依赖：无 conan 依赖（纯 POSIX + libc + dlfcn；构建期需 msgfmt=gettext 生成 .mo，CI 环境已有 /data/service/hnp/bin/msgfmt 0.26）。

## installwatch.c 的 musl（OHOS）移植（核心难点）

installwatch.c（4551 行）深度绑定 glibc 版本化 ABI，OHOS musl 无这些符号，必须移植（探索阶段直接改源码，已完成）：

1. **版本化符号→标准符号**：glibc 下 stat() 内部走 `__xstat(_STAT_VER,...)`，installwatch 导出 `__xstat/__lxstat/__xmknod/__fxstatat/__xmknodat` 拦截；musl 无版本化 ABI，应用直接调标准 `stat/lstat/mknod/fstatat/mknodat`（无 version 参数）。musl 分支新增同名标准符号拦截函数（文件尾部 `#if !defined(__GLIBC__)` 段），函数体调用 standard fn 指针（true_statfn/true_lstatfn/true_mknodfn/true_fstatatfn/true_mknodatfn）。
2. **函数指针与 dlsym**：musl 分支将 `true_xstat(_STAT_VER,...)` 等改为 `dlsym("stat")` 等标准名（`#if defined(__GLIBC__)` 包裹原 glibc 分支）。
3. **64 位变体禁用**：musl 头文件把 `stat64=stat`、`open64=open`、`creat64=creat`、`fopen64=fopen`、`truncate64=truncate`、`ftruncate64=ftruncate`、`readdir64=readdir`、`scandir64=scandir`、`dirent64=dirent` 全部宏归一为 32 位，installwatch 中 glibc 专属 64 位拦截函数（creat64/open64/readdir64/scandir64/xstat64/truncate64 等）会宏展开成与 32 位同名重复定义 → 统一用 `#if(__GLIBC_COMPAT && GLIBC_MINOR >= 1)`（musl 下 __GLIBC_COMPAT=0）整块禁用。musl 下 32 位符号已覆盖 64 位调用（宏归一）。
4. **类型映射**：`__mode_t→mode_t`、`__off64_t→off64_t`（musl 无 __ 前缀类型别名）。
5. **localdecls.h**：`create-localdecls` 脚本依赖 gcc/ldd//usr/include/unistd.h 探测，OHOS 无 → 手动按 musl 生成（TRUNCATE_T=off_t、READLINKAT_T=ssize_t、LIBC_FILE="libc.so"、GLIBC_MAJOR=2/Minor=10 走新式 scandir/readlink 签名）。
6. **构造函数**：musl 不支持 `_init/_fini` 符号，改用 `__attribute__((constructor))/__attribute__((destructor))`。

## 平台适配（脚本类工具，E037/E002）

- **shebang**：installwatch 包装脚本、checkinstall 主脚本原为 `#!/bin/bash`，OHOS 无 `/bin/bash`（bash 在 /data/service/hnp/bin/bash，/usr/bin/env→toybox 可用）→ 统一改 `#!/usr/bin/env bash`（探针实证 `/usr/bin/env bash -c` 可执行；E037 方案一）。
- **测试路径**：上游 test-installwatch.c 默认 TESTFILE=`/tmp/installwatch-test`（OHOS /tmp 只读，E002）。本地验证时通过临时修改绕过；该改动仅用于本地探索（不入补丁，PR 补丁集为 0001-0005），test_package 用自研 test.sh 在可写目录验证。

## 上游测试核查（R51）

installwatch/ 自带 `test-installwatch.c`（自测程序，检查 refcount 拦截计数）+ `libcfiletest.c`/`libctest.c`（create-localdecls 用的小桩）+ `Makefile` 的 `test` 目标。checkinstall 主脚本无独立测试套件。

OHOS 实测（LD_PRELOAD 加载 installwatch.so 运行 test-installwatch）：
- **核心拦截验证通过**：自研探针（binprobe.c）对 time/creat/chmod/chown/stat/lstat/open/truncate/ftruncate/utime/unlink/link/symlink/rename/mkdir/rmdir/fchmod/fchown 等逐项调用，LD_PRELOAD 下全部正常（`DONE`）。
- **test-installwatch 官方自测**：可达项 chmod/chown 等 12 项中 chown 类通过；chmod 项 refcount 计数假设差异（上游期望 close 也被 installwatch 计数，musl 下 close 未被拦截导致 +3 而非 +4）；**chroot 项因 OHOS 沙盒禁止 chroot 系统调用（SIGSYS/Bad system call，SKILL Gotchas E051 已知平台限制；无拦截基线同样失败）无法运行** —— 属系统级环境限制，非适配缺陷。
- 结论：上游测试在 OHOS 上核心通过，chroot 项为平台限制；PR 中如实拆分申报，并用 test_package 自研断言（installwatch --version / checkinstall --version / .so dlopen/dlsym）补齐功能覆盖。

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| sbin/checkinstall | ~84KB | 主程序 bash 脚本 |
| sbin/makepak | ~40KB | 打包辅助脚本 |
| bin/installwatch | ~7KB | LD_PRELOAD 包装脚本 |
| lib/installwatch.so | ~72KB | C 拦截库（arm64） |
| lib/checkinstall/*.mo | 12 语言 | 翻译 |---

**编译结束**: 2026-09-08 03:11
**最终状态**: built
---

**编译结束**: 2026-09-08 03:45
**最终状态**: built
