/*
 * stub-pthread.c — minimal pthread stub for HarmonyOS
 *
 * OHOS libpthread.a 无 pthread_cancel / pthread_setcanceltype（pthread
 * 子集——无线程取消功能）——autodir.c 的 autodir_clean/signal_handle
 * 调用它们——本 stub 提供空实现（线程取消不可用——返回 0/ENOSYS——
 * autodir 主功能正常——MANIFEST 如实申报，同 libltdl stub 先例）。
 *
 * 构建: clang -c stub-pthread.c && ar rcs libpthread_stub.a stub-pthread.o
 */
#include <pthread.h>
#include <errno.h>

int pthread_cancel(pthread_t thread) { (void)thread; return ENOSYS; }

int pthread_setcanceltype(int type, int *oldtype) { (void)type; if (oldtype) *oldtype = 0; return 0; }
