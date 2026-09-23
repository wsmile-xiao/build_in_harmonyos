# DRAFT: Android 出身 C 库迁移 OHOS 的四类通用适配点

- **适用场景**：任何 Android 出身（ndk-build / Android.mk / 带 JNI）的纯 C 库移植到 OHOS musl
- **错误签名**：`fatal error: 'android/log.h' file not found`、`fatal error: 'jni.h' file not found`、`use of undeclared identifier 'PAGE_MASK'`、`tentative definition ... 'struct sigaction' that is never completed`、`use of undeclared identifier 'DT_ANDROID_REL'`
- **根因**：bionic 与 musl 的四类差异——liblog 日志设施、JNI 头文件、elf.h 的 DT_ANDROID_* 打包重定位 tag、用户态 PAGE_MASK 宏与 sigaction 可见性
- **修法**（详见配对 .kv）：
  1. `__OHOS__` 分支用 `<hilog/log.h>` + 本地数值兼容枚举桥接 `__android_log_print → OH_LOG_Print`（LogLevel 3..7 与 android_LogPriority 完全一致，优先级过滤逻辑零改动），链接 `-lhilog_ndk.z`
  2. JNI 桥源文件整体 `#if !defined(__OHOS__)` 守卫
  3. `DT_ANDROID_REL/RELA/RELSZ/RELASZ`（0x6ffffee0..e3）`#ifndef` 补定义
  4. `PAGE_MASK` 由 `sysconf(_SC_PAGESIZE)` 派生；`xh_core.c` 显式 `#include <signal.h>`；配 `-D_GNU_SOURCE`（`-std=c11` 下 musl 隐藏完整 sigaction）
- **构建系统**：上游仅 Android.mk 时，conanfile 直接驱动 clang 按原源文件清单与 CFLAGS 编译（编译器来自 `tools.build:compiler_executables`，R33），无需为上游发明 CMake
- **验证**（xhook 1.2.0 实证）：本地 conan create 全绿；PLT hook 实测生效（malloc 重定向计数递增 + old_func 捕获 GOT 原值）；全 API 面（register/ignore/refresh sync+async/enable_debug/enable_sigsegv_protection/clear）返回 0
- **来源 PR**：xhook-1.2.0（2026-09-12）
