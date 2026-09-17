/*
 * OHOS 适配垫片 —— 仅供**引导编译器**使用。
 *
 * 为什么需要它：
 *   上游预编译 ldc2 自带的 libdruntime-ldc.a 在 core.thread.osthread 里引用
 *   pthread_setcancelstate / pthread_setcanceltype / pthread_testcancel /
 *   pthread_cancel，而 OHOS 的 musl 变体不导出这一家族（实测 libc.so 的
 *   1595 个导出符号里一个都没有，对照 pthread_create 存在）。
 *   LDC 的 CMake 在 configure 阶段会用引导编译器链接若干探测用 D 程序
 *   （如 ExtractDMDSystemLinker），若不提供该家族符号，这些链接会直接失败：
 *
 *       ld.lld: error: undefined symbol: pthread_setcancelstate
 *       >>> referenced by osthread.d
 *       >>>   osthread.o:(thread_cancelDisable) in archive .../libdruntime-ldc.a
 *
 *   故以本垫片提供 no-op 回退，并作为 -L 参数喂给引导编译器。
 *
 * 与源码补丁的关系：
 *   本包从源码构建的 druntime 由 patches/0001 直接改成上游的 no-op 分支，
 *   不依赖本垫片；本垫片只服务于「用上游预编译引导编译器链接探测程序」这一步，
 *   不会进入最终交付产物。
 */

#include <pthread.h>

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    (void)state;
    return 0;
}

int pthread_setcanceltype(int type, int *oldtype)
{
    if (oldtype)
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    (void)type;
    return 0;
}

void pthread_testcancel(void) {}

int pthread_cancel(pthread_t t)
{
    (void)t;
    return 0;
}

/* glibc 特有：druntime 的 core.internal.elf.dl 引用它读取程序名。
   须为 char*（与 druntime 的 extern 声明一致）。 */
char *program_invocation_name = (char *)"";
char *program_invocation_short_name = (char *)"";
