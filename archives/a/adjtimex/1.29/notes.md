# adjtimex 1.29 适配 notes

## 环境
- TMPDIR=/storage/Users/currentUser/tmp（/tmp 只读）
- CC=clang (15.0.4 aarch64-unknown-linux-ohos), 无 gcc
- 上游源码: http://deb.debian.org/debian/pool/main/a/adjtimex/adjtimex_1.29.orig.tar.gz (85551 bytes)

## 适配问题与修复（探索阶段，将固化为补丁）
1. configure 生成的 config.status 中 `(umask 077 && mktemp -d "./confXXXXXX")` 创建 0700 临时目录，
   HMDFS 下属主映射为 20001006，当前用户 20020083 无法写入 → Permission denied。
   修复：configure 两处 `umask 077` → `umask 002`（组可写）。
2. Makefile.in `bindir=/sbin` 写死 → 改为 `$(prefix)/sbin`。
3. Makefile.in install 使用 `-o root -g bin`（鸿蒙无 root/chown 受限）→ 移除，
   并补 `$(INSTALL) -d` 创建 bindir 目录，改用 DESTDIR 前缀。

## 系统层面差异（需回报）
- `sys/timex.h` 存在于 SDK sysroot，`struct timex` 完整，`adjtimex()` 可编译链接。
- 但运行期 `adjtimex()` 系统调用被鸿蒙 seccomp 沙箱拦截：SIGSYS (si_signo=31, si_code=1=SYS_SECCOMP)。
  - syscall(SYS_adjtimex=171) 直接触发 SIGSYS core dump，errno=0。
  - `adjtimex` 默认无参/`--print` 模式 → SIGSYS core dump。
  - `adjtimex --version` → 正常输出 "adjtimex 1.29"，exit 0（不调用 adjtimex syscall）。
- `linux/timex.h` 与 musl 头文件冲突（timespec/timeval/itimerval/timezone/timex 重定义），
  上游源码仅 include `sys/timex.h`，不受影响。
- smoke test 使用 `adjtimex --version`（不触发 syscall），退出码 0。
- `--print`/调时功能在鸿蒙沙箱不可用，真实通过率按可执行路径统计。

## 测试
- 上游无官方测试套件（无 test/ 目录、无 check target、configure.in 无测试配置）。
- 新增 smoke test：`adjtimex --version` 验证退出码 0。
---

**编译结束**: 2026-08-04 18:43
**最终状态**: built
