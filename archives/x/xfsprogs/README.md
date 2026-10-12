# xfsprogs 7.2.0 - HarmonyOS 编译记录

## 概述

xfsprogs 是 XFS 文件系统工具集（mkfs.xfs / xfs_repair / xfs_db / xfs_io / xfs_quota / xfs_scrub 等）。

**编译状态**: ✅ 编译成功（12 个工具版本探针全部通过；未执行真实格式化/修复操作）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel 1.12.0 aarch64 |
| 编译器 | clang 15.0.4（OHOS SDK） |
| C 库 | musl libc（OHOS SDK sysroot） |
| 三元组 | aarch64-unknown-linux-ohos |
| 依赖 | inih/r58、libuuid/2.40.4、liburcu/0.15.6、libblkid/2.42.2（静态链接，产物 NEEDED 仅 libc.so） |

## 编译步骤

1. 应用 11 个补丁（见 `patches/`，说明见 notes.md 与版本 manifest）
2. `./configure --prefix=/ --enable-gettext=no`
   （依赖 include 经 CFLAGS/CXXFLAGS 注入；LDFLAGS 指向依赖私有目录；LIBS 仅 -lurcu）
3. `make -j1`
4. `make install DESTDIR=<package>`
5. `conan create` + test_package（AArch64 ELF 校验 + 工具 -V 实跑）

## 补丁说明

| 补丁 | 内容 |
|------|------|
| 0001-config.guess | HarmonyOS 系统识别（aarch64-unknown-linux-ohos） |
| 0002-config.sub | ohos-linux 三元组 / linux-ohos 内核组合 |
| 0003-configure | 临时目录 umask 077→022（HMDFS 0700+setgid 不可写） |
| 0004-doc-Makefile | gzip --best→-9（toybox gzip 不支持 --best） |
| 0005-include-fsmap_compat.h | 补齐 OHOS SDK 缺失的 fsmap UAPI inline 函数 |
| 0006-install-sh | shebang→/bin/sh；id(1) 缺失时 REAL_UID 回退 |
| 0007/0010/0011 | fsmap 调用方改用 fsmap_compat.h |
| 0008-io-healthmon.c | case 标签后声明上移（clang 15 不支持 C23） |
| 0009-mkfs-proto.c | 本地实现 xfs_reallocarray（OHOS libc 无该函数） |

## 已知限制

- NLS 本地化消息关闭（平台无 msgmerge；gettext 制品包仅 libintl）
- xfs_scrub 未启用 libicu（上游 probe 可选项，unicode 名称扫描关闭）
- 未运行 xfstests（需要真实块设备与破坏性操作，CI 不可行）

## 验证结果

| 测试项 | 结果 |
|--------|------|
| configure / make / make install | ✅ RC=0 |
| 12 个工具 `-V` | ✅ 全部 rc=0 |
| test_package R53（AArch64 ELF 校验） | ✅ 5 工具断言通过 |
| test_package R34（工具实跑） | ✅ smoke.sh 5 工具 -V rc=0 |
| 真实格式化/修复操作 | ⛔ 未执行（安全考虑） |
