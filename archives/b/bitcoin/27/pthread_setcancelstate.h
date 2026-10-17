/* OHOS musl 无 pthread_setcancelstate API（API 裁剪缺失）——
 * 提供空操作 stub（OHOS musl 无线程取消机制，PTHREAD_CANCEL_ENABLE 恒真）。
 * 经 -include 强制注入，供 boost sp_thread_sleep.hpp 等引用。 */
#ifndef OHOS_PTHREAD_SETCANCELSTATE_STUB_H
#define OHOS_PTHREAD_SETCANCELSTATE_STUB_H

#include <pthread.h>

#ifndef PTHREAD_CANCEL_ENABLE
#define PTHREAD_CANCEL_ENABLE 0
#endif

static inline int
pthread_setcancelstate (int state, int *oldstate)
{
  (void) state;
  if (oldstate != NULL)
    *oldstate = PTHREAD_CANCEL_ENABLE;
  return 0;
}

#endif
