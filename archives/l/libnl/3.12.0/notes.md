# libnl 3.12.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 目标平台: aarch64-unknown-linux-ohos (OpenHarmony)
- 状态: built

## 编译步骤

```bash
source .build-context-libnl-3.12.0
cd $BUILD_SRC_DIR
export PATH="$HOME/tmp/toolbox-wrap:$PATH"

# 1. 修补 config.guess/config.sub（平台识别）
# 已通过 patch-autotools-ohos.pl 修补

# 2. 运行 configure（必须用 /bin/sh 而非 bash）
/bin/sh ./configure --prefix=$DEFAULT_PREFIX

# 3. 修补 config.status 中的 umask 077→022（HMDFS 权限问题）
sed -i 's/umask 077/umask 022/g' config.status

# 4. 手动运行 config.status 生成 Makefile
sh config.status

# 5. 编译
make -j1

# 6. 安装到 DESTDIR
make install DESTDIR=$TEST_PREFIX

# 7. 本地安装验证
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 原始 config.guess 不包含 ohos 识别规则 | 用 patch-autotools-ohos.pl 修补 config.guess/config.sub |
| 2 | configure 中 rm/ls 命令找不到 | bash 无法执行 /usr/bin/ 下的 toybox 命令 | 使用 /bin/sh (toybox sh) 替代 bash 运行 configure |
| 3 | config.status 创建临时文件 Permission denied | HMDFS 文件系统：umask 077 创建的目录无组权限，阻止内部文件创建 | 将 config.status 中 umask 077 改为 umask 022 |
| 4 | GNU head 报 "cannot seek" 错误 | GNU coreutils 的 fstat/lseek 对管道 FD 返回 EACCES | 使用 ~/tmp/toolbox-wrap/ 中 toybox 符号链接替代 GNU coreutils |
| 5 | make check 测试编译失败 | 测试程序需要 linux/pkt_sched.h 等内核头文件，HarmonyOS SDK 缺失 | 非关键问题，核心库编译成功，测试跳过 |

## 源码修改

- `build-aux/config.guess`: 添加 aarch64-unknown-linux-ohos 平台识别
- `build-aux/config.sub`: 允许 aarch64-unknown-linux-ohos 作为合法三元组
- `configure` (运行时修改): umask 077 → umask 022 (HMDFS 兼容性)
- `config.status` (运行时修改): umask 077 → umask 022 (HMDFS 兼容性)

## 依赖版本

- clang (系统自带)
- flex 2.6.4
- bison 3.8.2
- pkg-config 0.29.2
- gawk (系统自带)
- make 4.4.1
- llvm-ar / llvm-nm / llvm-ranlib / llvm-strip / ld.lld

## 验证结果

```bash
# 头文件验证
ls ~/usr/local/include/libnl3/netlink/msg.h
# → 存在 ✅

# 静态库验证
ls ~/usr/local/lib/libnl-3.a
# → 存在 ✅ (226040 bytes)

# 动态库验证
ls ~/usr/local/lib/libnl-3.so
# → 存在 ✅ (symlink → libnl-3.so.200.26.0)

# pkg-config 验证
pkg-config --modversion libnl-3.0
# → 3.12.0 ✅

# ELF 架构验证
readelf -h ~/usr/local/lib/libnl-3.so.200.26.0
# → ELF64, AArch64, DYN (Shared object) ✅

# 安装产物统计
# 7 个共享库: libnl-3, libnl-route-3, libnl-genl-3, libnl-nf-3, libnl-idiag-3, libnl-xfrm-3, libnl-cli-3
# 7 个静态库: 对应 .a 版本
# 7 个 pkg-config 文件
# 46 个 CLI 工具 (nl-*, genl-*, nf-* 等)
# 大量头文件 (netlink/ 子目录)
```

## 测试结果

make check 因测试程序需要 Linux 内核头文件 (linux/pkt_sched.h) 而**编译失败**，
HarmonyOS SDK 不包含这些头文件。configure 已自动检测并禁用 unit tests (check >= 0.9.0)。
核心库编译和安装成功，测试跳过不影响库的使用。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnl-3.12.0-ohos-aarch64.tar.gz | ~10MB | 预编译包（含共享库、静态库、头文件、CLI工具、pkg-config） |
| libnl-3.12.0-ohos-aarch64-debug.tar.gz | ~2.5MB | 调试符号包 |

## 注意事项

1. 运行 configure 必须用 `/bin/sh` 而非 bash（HMDFS bash/toybox 权限问题）
2. 运行 autotools 脚本前需设置 PATH 含 ~/tmp/toolbox-wrap/（解决管道兼容问题）
3. config.status 生成后必须修补 umask 077→022（HMDFS 权限模型问题）
4. libnl 是网络库，部分 CLI 工具需要 root 权限或网络接口才能正常运行 --version

---
**编译结束**: 2026-05-28 14:46
**最终状态**: built
---

**编译结束**: 2026-06-01 17:04
**最终状态**: built
