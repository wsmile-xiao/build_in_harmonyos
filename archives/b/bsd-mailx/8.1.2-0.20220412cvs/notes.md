# bsd-mailx 8.1.2-0.20220412cvs 适配笔记

## 编译环境
- 构建系统: makefile（上游 OpenBSD bsd.prog.mk，适配改写为 GNU make 兼容）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（aarch64-linux-ohos 交叉编译）
- 状态: built

## 编译步骤

```bash
# 源码获取（Debian 官方 pool 权威镜像）
# http://deb.debian.org/debian/pool/main/b/bsd-mailx/bsd-mailx_8.1.2-0.20220412cvs.orig.tar.xz

# 构建（无 configure，直接 make）
make -j1 CC="clang --target=aarch64-linux-ohos --sysroot=$SYSROOT" \
  CFLAGS="-D_DEFAULT_SOURCE -D_BSD_SOURCE -g -Wall -O2"

# 安装（标准布局 BINDIR=bin）
make install DESTDIR=$TEST_PREFIX

# Conan 配方验证（8 道门禁全过）
ohc-run.py conan-verify bsd-mailx 8.1.2-0.20220412cvs
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bsd.prog.mk 无法在 OHOS 构建 | 上游 Makefile 是 OpenBSD 专用（`.include <bsd.prog.mk>`），GNU make 不识别 | 改写为 GNU make 兼容 Makefile（patch 0001） |
| 2 | `vis.h` 不存在 | OHOS libc 无 BSD vis(3) API（strvis/strnvis） | 移植 OpenBSD 官方 vis.c/vis.h，经 conanfile exports_sources 随配方打包（不引入 libbsd 依赖） |
| 3 | `__va_list` 未定义 | OpenBSD 特有类型，OHOS 无 | 改为标准 `va_list`（patch 0003） |
| 4 | `pledge()` 不存在 | OpenBSD 特有 syscall | 删除调用（同 Debian 31 patch）（patch 0006） |
| 5 | `user_from_uid`/`uid_from_user` 未定义 | BSD libutil 特有函数 | 改用 POSIX `getpwuid`/`getpwnam`（patch 0013） |
| 6 | `warnc()` 未定义 | BSD err.h 特有（带 errno 参数的 warn） | 提供兼容实现（patch 0005） |
| 7 | `GLOB_BRACE`/`ALTWERASE`/`CCEQ`/`_PATH_CSHELL` 未定义 | OHOS libc 缺失 BSD/GNU 扩展 | `#ifndef` 兼容守卫（patch 0004/0008/0011） |
| 8 | `OPEN_MAX` 未定义 | OHOS 无此宏 | 改用 `FOPEN_MAX`（同 Debian 27 patch）（patch 0012） |
| 9 | `/tmp` 只读（E002 陷阱） | OHOS 设备 /tmp 只读，bsd-mailx 固定用 /tmp 作临时目录 | 适配遵循 `$TMPDIR` 环境变量（同 Debian 36 patch）（patch 0010） |
| 10 | conan create 打包失败 | OHOS `install` 命令不支持 `-p -c` 选项、不支持多源安装 | Makefile install 改为单文件 `install -m MODE`（patch 0001） |
| 11 | `LOCK_EX` 未定义 | quit.c 缺 `sys/file.h` | 补头文件（patch 0009） |
| 12 | `ctime` 隐式 int | names.c/util.c 缺 `time.h` | 补头文件（patch 0007/0012） |

## 源码修改

15 个补丁（13 个跟踪文件补丁 + 2 个新增 vis 文件走 exports_sources）：
- patches/0001-Makefile.patch — GNU make 兼容 + 标准 BINDIR 布局 + install 兼容
- patches/0002-def.h.patch — vis.h 本地引用 + stdarg.h
- patches/0003-extern.h.patch — __va_list → va_list
- patches/0004-fio.c.patch — GLOB_BRACE 兼容
- patches/0005-lex.c.patch — warnc 兼容实现
- patches/0006-main.c.patch — 删除 pledge
- patches/0007-names.c.patch — 补 time.h
- patches/0008-pathnames.h.patch — _PATH_CSHELL 回退
- patches/0009-quit.c.patch — 补 sys/file.h
- patches/0010-temp.c.patch — $TMPDIR 支持
- patches/0011-tty.c.patch — ALTWERASE/CCEQ 兼容
- patches/0012-util.c.patch — OPEN_MAX→FOPEN_MAX + time.h
- patches/0013-v7.local.c.patch — user_from_uid→getpwuid
- vis.c/vis.h（新增文件，OpenBSD 官方源移植，exports_sources 打包）

## 依赖版本

零外部依赖（无 requires）。不引入 liblockfile/libbsd：
- liblockfile 是 Debian 特有安全修复（setgid 方案），非上游硬依赖
- libbsd 仅为 strlcpy/strvis 提供，OHOS musl 已含 strlcpy/strlcat，vis 用移植实现替代

## 验证结果

```bash
# 本地功能验证（自研测试 9 断言全过）
python3 test_package/test_bsd_mailx.py build/mail
# → bsd-mailx functional tests passed (9 assertions)

# Conan 配方验证 8 道门禁
conan-verify → G1/G2/G3/G4/L2/L4/L5 全部 PASS

# W3 本地 CI 模拟
build_and_test.sh → L0 pass / L1 pass / L1e pass / L4 pass / L5 pass（1/1 成功）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bsd-mailx | 主程序（mailx 命令行邮件客户端） |
| share/man/man1/bsd-mailx.1 | man 手册 |
| etc/mail.rc | 全局配置文件 |
| share/bsd-mailx/mail.help, mail.tildehelp | 帮助文件 |

## 注意事项

- 发送邮件依赖外部 sendmail（`/usr/sbin/sendmail`），OHOS 默认无此命令；`-f` 读取 mailbox、交互命令等核心功能完整可用
- 上游无测试用例（穷尽核查：无 tests/ 目录、无 test/check 目标、无测试钩子），test_package 以自研功能测试集补全覆盖（4 组 9 断言）
---

**编译结束**: 2026-09-07 04:09
**最终状态**: built
