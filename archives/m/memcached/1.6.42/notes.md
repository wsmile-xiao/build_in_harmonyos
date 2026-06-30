# memcached 1.6.42 编译笔记

## 编译状态
状态: partial（部分成功）

## 问题与解决

### 问题1: config.status 临时文件创建失败
- 错误: `./config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`
- 解决: 修改 configure 脚本，使用 `$TMPDIR` 替代当前目录

### 问题2: mremap syscall 不支持
- 错误: PSCAN-MUSL-002 critical
- 解决: 在 linux_priv.c:154 用 `#ifdef __OHOS__` 排除 mremap seccomp 规则

### 问题3: HarmonyOS 平台识别失败
- 错误: `configure: error: cannot guess build type`
- 解决: 使用 patch-autotools-ohos.pl 补丁脚本

## 预编译包
- memcached-1.6.42-ohos-aarch64.tar.gz (583K)
- memcached-1.6.42-ohos-aarch64-debug.tar.gz (629K)

---
编译结束: 2026-06-04
最终状态: partial
