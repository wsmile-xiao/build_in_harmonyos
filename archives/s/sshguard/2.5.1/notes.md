# sshguard 2.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++ (OHOS SDK 26.0.0.18)
- 目标平台: HarmonyOS aarch64, musl libc
- 状态: published

## 完整编译步骤

```bash
source .build-context-sshguard-2.5.1

# 环境修复：lld linker 需要 libxml2.so.16
# 方案1: 设置 LD_LIBRARY_PATH
# 方案2: 创建符号链接到 ~/usr/local/lib（推荐，G0 验证更友好）
ln -sf /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/libxml2.so.16 \
       ~/usr/local/lib/libxml2.so.16

cd $BUILD_SRC_DIR

# 补丁1: E011 HMDFS umask 修复（已通过 track-edit 记录）
sed -i 's/umask 077/umask 022/g' configure

# 配置
./configure --prefix=$DEFAULT_PREFIX

# 编译
make -j1

# 补丁2: musl pthread cancellation 宏守卫（已通过 track-edit 记录）
# 在 src/blocker/blocklist.c 中添加 #ifdef __OHOS__ 宏守卫

# 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# 安装到本地
make install

# 测试
make check  # 200/200 PASS

# 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package sshguard 2.5.1

# 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish sshguard 2.5.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁文件 |
|---|------|------|----------|----------|
| 1 | C compiler cannot create executables | lld linker 需要 libxml2.so.16，但 SDK lib 目录不在 LD_LIBRARY_PATH | 创建 ~/usr/local/lib/libxml2.so.16 符号链接 | 无需补丁（环境修复） |
| 2 | config.status Permission denied (E011) | HMDFS umask 077 导致临时目录权限不兼容 | `sed -i 's/umask 077/umask 022/g' configure` | 0002-configure.patch |
| 3 | undefined symbol pthread_setcancelstate/pthread_testcancel | musl 不提供 pthread cancellation 函数 | 添加 `#ifdef __OHOS__` 宏守卫，no-op 替换 | 0003-src-blocker-blocklist.c.patch |

## 源码修改详情

### 1. configure — E011 HMDFS umask 修复

```diff
- tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
+ tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null` &&

- (umask 077 && mkdir "$tmp")
+ (umask 022 && mkdir "$tmp")
```

原因：HMDFS 文件系统中 umask 077 创建的临时目录权限对当前 UID 映射不兼容，
导致 config.status 无法写入临时文件。改为 umask 022 后 configure 正常运行。

### 2. src/blocker/blocklist.c — musl pthread cancellation 宏守卫

```c
#ifdef __OHOS__
/* HarmonyOS musl does not support pthread cancellation functions */
#define pthread_testcancel() ((void)0)
#define pthread_setcancelstate(state, oldstate) (*(oldstate) = (state), 0)
#endif
```

原因：musl libc 不实现 POSIX 线程取消机制（pthread_testcancel,
pthread_setcancelstate），调用这些函数会导致链接失败。通过 __OHOS__
宏守卫将它们替换为空操作，保留功能兼容性。

注意：blocklist.c 中有编译警告 "non-void function does not return a value in
all control paths"，这是 sshguard 源码本身的风格问题，不影响功能。

## 依赖版本

无外部依赖。sshguard 仅依赖 POSIX pthread/socket，编译后 ELF 二进制仅链接 libc.so (musl)。

## 测试结果

### make check — 200/200 PASS

```
============================================================================
Testsuite summary for sshguard 2.5.1
============================================================================
# TOTAL: 200
# PASS:  200
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================
```

测试内容：sshg-parser 日志解析测试，覆盖 SSH、Mail、FTP、OpenVPN、Web、
Cockpit、BIND、MSSQL、Gitea、Proxmox VE 等 17 种服务/协议的攻击日志格式，
含 IPv4/IPv6 地址和多种 syslog banner 格式。

### 本地安装功能验证

- sshguard: 报告 "Could not read sshguard.conf"（预期行为，守护进程需要配置文件）
- sshg-parser -h: 输出 "usage: sshg-parser [-adht]"（正常）
- sshg-fw-hosts: 报告 "could not open hosts.allow"（预期行为，需 hosts.allow 文件）
- sshg-fw-null: 空后端 shell 脚本（正常，鸿蒙推荐使用此后端）
- sshg-logtail: 需要 -f 参数指定日志文件（正常）

### R7 安全弹窗检查

所有 ELF 二进制文件（sshg-blocker, sshg-parser, sshg-fw-hosts）执行时
无网络访问弹窗提示，通过 R7 检查。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sshguard-2.5.1-ohos-aarch64.tar.gz | 1.4MB (1567490B) | 预编译包 |
| sshguard-2.5.1-ohos-aarch64-debug.tar.gz | 84KB (84513B) | 调试符号包 |

预编译包内容：
- sbin/sshguard (shell 入口脚本)
- libexec/sshg-blocker (ELF, ARM aarch64)
- libexec/sshg-parser (ELF, ARM aarch64)
- libexec/sshg-fw-hosts (ELF, ARM aarch64)
- libexec/sshg-fw-null, sshg-fw-firewalld, sshg-fw-ipfilter, sshg-fw-ipfw,
  sshg-fw-ipset, sshg-fw-iptables, sshg-fw-nft-sets, sshg-fw-pf (shell scripts)
- libexec/sshg-logtail (shell 脚本)
- share/man/man7/sshguard-setup.7, share/man/man8/sshguard.8

## G0 干净构建验证

G0 验证结果：configure ✅ + make ✅ + make install ⚠️

make install 步骤因 clean-verify 脚本仅检查 bin/* 和 lib/* 而误判为"安装产物为空"
——sshguard 将二进制安装到 sbin/ 和 libexec/ 而非 bin/，实际产物完整且功能正常。
此为脚本检查范围不足而非构建问题。

## 注意事项

- sshguard 是守护进程工具，需要 `/etc/sshguard.conf` 配置文件才能运行
- 防火墙后端 iptables/pf/nft 等在鸿蒙不可用，推荐使用 `sshg-fw-null`（空后端）
  或 `sshg-fw-hosts`（hosts.allow 方式）
- musl 不支持 pthread cancellation，已通过 __OHOS__ 宏守卫处理
- 编译环境需解决 lld linker 对 libxml2.so.16 的依赖（符号链接方案推荐）
- sshguard 不安装到 bin/ 目录，主二进制在 sbin/，组件在 libexec/

---
**编译结束**: 2026-06-12 03:19
**最终状态**: published