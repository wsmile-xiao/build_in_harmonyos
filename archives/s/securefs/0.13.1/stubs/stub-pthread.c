/*
 * stub-pthread.c — POSIX 线程取消族的最小实现（HarmonyOS/OHOS 适配）
 *
 * 背景：OHOS 的 libc（musl 系）不提供 POSIX 线程取消 API ——
 *   pthread_cancel / pthread_setcancelstate / pthread_setcanceltype /
 *   pthread_testcancel 均无定义（知识库 E085 记录的是同一类缺口）。
 *
 * 触发点：本包静态链接 libfuse/2.9.9 的 libfuse.a，其 fuse.c 的
 *   fuse_stop_cleanup_thread() 与 fuse_loop_mt.c 的 fuse_do_work() /
 *   fuse_session_loop_mt() 引用 pthread_cancel 与 pthread_setcancelstate，
 *   链接期报 ld.lld: error: undefined symbol（详见 reports/）。
 *
 * 处理：提供空实现（no-op），让链接通过并保持主功能可用。
 *   语义代价（如实申报，见 manifest.yaml / notes.md）：
 *   - pthread_cancel 不会真正取消目标线程（返回 0，表示"已请求"）；
 *   - pthread_setcancelstate/setcanceltype 记录/回填旧值后直接返回；
 *   - pthread_testcancel 直接返回。
 *   因此 securefs 在 OHOS 上多线程 FUSE 循环的"取消清理线程"路径不可用：
 *   如需卸载挂载点，应避免依赖线程取消（单线程循环 fuse_loop 不受影响）。
 *   同仓先例：archives/a/autodir/0.99.9/stubs/stub-pthread.c、archives/a/alpine/2.26。
 *
 * 构建由 conanfile.py 的 generate() 用 OHOS clang 完成（非 CMake 目标），
 * 产物 libohos_pthread_stub.a 追加进 FUSE_LIBRARIES 参与链接。
 */
#include <pthread.h>

int pthread_cancel(pthread_t thread)
{
    (void)thread;
    return 0;
}

int pthread_setcancelstate(int state, int *oldstate)
{
    (void)state;
    if (oldstate)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    return 0;
}

int pthread_setcanceltype(int type, int *oldtype)
{
    (void)type;
    if (oldtype)
        *oldtype = PTHREAD_CANCEL_DEFERRED;
    return 0;
}

void pthread_testcancel(void)
{
}
