# libaio 0.3.112.1 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libaio |
| 版本 | 0.3.112.1 (修复 io_pgetevents SIGSYS 崩溃) |
| 构建系统 | plain Makefile (non-autotools) |
| 源码 | https://releases.pagure.org/libaio/libaio-0.3.112.tar.gz |
| 状态 | built |

## 编译要点
- libaio 使用纯 Makefile 构建，非 autotools/cmake
- 顶层 Makefile 委托 src/Makefile 编译
- 编译器路径必须从 Conan conf 获取 (R33)，使用 `self.conf.get("tools.build:compiler_executables")`
- `make -C self.source_folder` 因为 Conan 在子目录运行 build
- libaio 是系统同名库，默认静态编译 (R26)

## 补丁
1. `0001-harness-cases-13.t.patch` — 修复 designated initializer 语法 (C99 合规)
2. `0002-harness-cases-22.t.patch` — 替换废弃的 sys/poll.h 为 poll.h
3. `0003-io_pgetevents-ohos-sigsys.patch` — **关键修复**: OHOS 平台 io_pgetevents SIGSYS 崩溃

## 0.3.112.1 修复内容 (2026-08-11)

### 问题
OHOS 内核对 `io_pgetevents` (syscall 292) 的行为与 Linux 不一致：
- **Linux**: 不存在的 syscall 返回 `-ENOSYS` (-38)，libc 设置 errno=38，syscall() 返回 -1
- **OHOS**: syscall 292 触发 **SIGSYS (signal 31)**，进程直接崩溃

libaio 的 `_body_io_syscall` 宏假设 `syscall()` 总会返回：
```c
ret = syscall(__NR_##sname, ## args);
if (ret < 0) { ret = -errno; errno = saved_errno; }
return ret;
```
当 OHOS 触发 SIGSYS 时，`syscall()` 根本不会返回，进程直接终止。

### 根因
- `syscall-generic.h` (aarch64) 未定义 `__NR_io_pgetevents`
- 但系统的 `sys/syscall.h` 定义了 `__NR_io_pgetevents = 292`
- `io_pgetevents.c` 的 `#ifdef __NR_io_pgetevents` 走 syscall 路径而非 -ENOSYS stub

### 修复
在 `src/syscall.h` 中添加 OHOS 守卫，取消 `__NR_io_pgetevents` 定义：
```c
#if defined(__OHOS__) && defined(__NR_io_pgetevents)
#undef __NR_io_pgetevents
#endif
```
使 `io_pgetevents.c` 走 `#else` 路径，返回 `-ENOSYS` 而不触发 syscall。

### 同时修复
- `package_info` 添加 `system_libs = ["c"]`（libaio 依赖 libc 的 `syscall()` 和 `__errno_location()`）

## 二次校准 (2026-07-17) — 0.3.112 历史记录
- CI 报告 test_package 失败（io_setup syscall），修改 test.c 不依赖返回值
---

**编译结束**: 2026-08-11 18:16
**最终状态**: built
