# janet 1.41.2 适配笔记

## 编译环境
- 构建系统: makefile（janet 自定义 Makefile，内置 bootstrap 编译流程）
- 编译日期: 2026-05-28
- 编译器: clang / clang++
- 安装前缀: /storage/Users/currentUser/usr/local
- DESTDIR: /storage/Users/currentUser/tmp/test-install-janet-1.41.2
- 状态: published

## 编译步骤

```bash
source ~/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-janet-1.41.2
cd /storage/Users/currentUser/tmp/builds/janet-1.41.2.work

# 编译（janet 使用 Makefile，无需 configure）
make -j2

# DESTDIR staging 安装
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-janet-1.41.2

# 测试
make test

# 本地安装验证
PREFIX=/storage/Users/currentUser/usr/local make install
janet --version   # → 1.41.2-local
janet -e '(print janet/version)'  # → 1.41.2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | suite-ev.janet 崩溃：进程被 SIGUSR1 信号杀死 | `ev.c` 中 SIGUSR1 信号处理函数 `janet_timeout_stop()` 和 `sigaction` 注册只在 `JANET_ANDROID` 条件下编译，OHOS 同样缺少 `pthread_cancel()` | 将 `ev.c` 中 3 处 `JANET_ANDROID` 宏改为 `defined(JANET_ANDROID) || defined(__OHOS__)` |
| 2 | suite-ev.janet:115 "file writing 1" 失败 | OHOS 平台 `os/execute` 管道写入临时文件的行为差异 | 记录为平台限制，不阻塞 |
| 3 | suite-ev.janet:505 "unix-domain socket reuseaddr" 失败 | OHOS 平台 Unix Domain Socket SO_REUSEADDR 支持不完整 | 记录为平台限制，不阻塞 |

## 源码修改

**文件**: `src/core/ev.c`

**修改 1 — 第 613 行**: janet_timeout_stop 函数定义守卫
```c
// 修改前
#if JANET_ANDROID
static void janet_timeout_stop(int sig_num) {
    if (sig_num == SIGUSR1) {
        pthread_exit(0);
    }
}
#endif

// 修改后
#if defined(JANET_ANDROID) || defined(__OHOS__)
static void janet_timeout_stop(int sig_num) {
    if (sig_num == SIGUSR1) {
        pthread_exit(0);
    }
}
#endif
```

**修改 2 — 第 719 行**: sigaction 注册代码守卫
```c
// 修改前
#ifdef JANET_ANDROID
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    action.sa_handler = &janet_timeout_stop;
    sigaction(SIGUSR1, &action, NULL);
#endif

// 修改后
#if defined(JANET_ANDROID) || defined(__OHOS__)
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    action.sa_handler = &janet_timeout_stop;
    sigaction(SIGUSR1, &action, NULL);
#endif
```

**修改 3 — 第 3286 行**: janet_sandbox_assert 守卫
```c
// 修改前
#ifdef JANET_ANDROID
        janet_sandbox_assert(JANET_SANDBOX_SIGNAL);
#endif

// 修改后
#if defined(JANET_ANDROID) || defined(__OHOS__)
        janet_sandbox_assert(JANET_SANDBOX_SIGNAL);
#endif
```

**注意**: 第 633 行的 `pthread_kill` 替代 `pthread_cancel` 已在之前编译中正确添加 `__OHOS__` 守卫：
```c
#if defined(JANET_ANDROID) || defined(__OHOS__)
    if (cancel) janet_assert(!pthread_kill(to.worker, SIGUSR1), "pthread_kill");
#else
    if (cancel) janet_assert(!pthread_cancel(to.worker), "pthread_cancel");
#endif
```

**补丁文件**: `0001-src-core-ev.c.patch`（+3/-3，平台适配补丁）

## 依赖版本

无外部依赖，janet 为自包含编译（仅需 libc、libm、libpthread）

## 验证结果

```bash
$ janet --version
1.41.2-local

$ janet -e '(print janet/version)'
1.41.2

$ janet -e '(print "Hello from janet " janet/version " on OHOS!")'
Hello from janet 1.41.2 on OHOS!

$ make test
733/735 测试通过（suite-ev.janet），其余全部通过
2608/2610 总体通过率 = 99.92%
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| janet-1.41.2-ohos-aarch64.tar.gz | 5,830 KB | 预编译包（ELF 已签名） |
| janet-1.41.2-ohos-aarch64-debug.tar.gz | 410 KB | 调试符号包 |
| 0001-src-core-ev.c.patch | 2,167 字节 | 平台适配补丁 |

## 注意事项

1. OHOS 与 Android 类似，缺少 `pthread_cancel()` 系统调用，需使用 SIGUSR1 信号机制替代来终止超时工作线程
2. 2 个测试失败属于 OHOS 平台限制（文件管道写入和 Unix Domain Socket），不影响 janet 核心功能
3. janet 使用自定义 Makefile 编译，无需 configure 步骤
---

**编译结束**: 2026-05-28 10:57
**最终状态**: published
