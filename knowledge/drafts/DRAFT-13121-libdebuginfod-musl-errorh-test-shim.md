# DRAFT-13121: musl 无 error.h —— 上游测试程序调用 error()/error_at_line() 的 shim 注入模式

## 错误面

- 编译期:`fatal error: 'error.h' file not found`(测试源 `#include <error.h>`)
- 删除 include 后链接期:`undefined symbol: error`(error()/error_at_line() 实际调用点)

## 根因

glibc 的 `<error.h>` 声明 error(int,int,const char*,...) / error_at_line(...)
与全局量 error_message_count / error_one_per_line / error_print_progname;
musl 有意不提供。elfutils 0.195 tests/ 有 100+ 调用点、约 40 个程序,另有
仅 include 不调用的死 include。

## 修复模式(推荐:生成式 shim 头)

conan 配方 generate() 阶段把 error.h shim 写进 generators 目录并前置 `-I`:

- error(status, errnum, fmt, ...):fflush(stdout) → `program_invocation_short_name:` →
  可选 `strerror(errnum):` → vfprintf → 换行 → error_message_count++ → status 非零则 exit
- error_at_line(...):多 `filename:line:` 前缀,其余同上
- `program_invocation_short_name` 需 `-D_GNU_SOURCE`(musl 在此宏下暴露)
- 头内 static 实现:测试程序单用途,每 TU 私有副本无碍 pass/fail 语义

边界:
- 死 include(文件内无 error() 调用)用补丁删除即可,不必 shim
- pthread_cancel 测试程序**不可 shim**(musl 不实现 cancellation,桩会让线程
  永不停止→套件挂死)——应从 tests/Makefile.in 的 check_PROGRAMS/TESTS 剔除

## 实测

libdebuginfod 0.195(elfutils 0.195 源,make check TOTAL=292):
PASS 211 / SKIP 43 / FAIL 38(72.3%),shim 消解了全部 error.h 编译/链接错误。
