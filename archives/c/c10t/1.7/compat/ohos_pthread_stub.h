#pragma once
/* OHOS/musl libc compatibility shim for c10t (POSIX, no platform macro).
 *
 * musl-based libcs (OpenHarmony/HarmonyOS uses musl) do not implement the
 * POSIX thread-cancellation API (pthread_setcancelstate/setcanceltype).
 * Boost's sp_thread_sleep() calls pthread_setcancelstate() around
 * nanosleep(); on such libcs the identifier is undeclared and the build
 * fails (E127/E085). Newer Boost guards the calls behind a platform
 * macro, but the guard only helps when the compiler predefines it.
 *
 * This header is force-included via -include from the recipe generate()
 * step, so it is seen before any Boost header. On glibc the guard below
 * is false and the header is a no-op. On musl (linux without __GLIBC__)
 * the cancel calls are redirected to harmless no-ops: c10t only needs the
 * nanosleep delay, cancellation semantics are irrelevant here.
 */
#include <pthread.h>

#if defined(__linux__) && !defined(__GLIBC__)
#ifndef PTHREAD_CANCEL_DISABLE
#define PTHREAD_CANCEL_DISABLE 0
#endif
#ifndef PTHREAD_CANCEL_ENABLE
#define PTHREAD_CANCEL_ENABLE 1
#endif
#ifndef PTHREAD_CANCEL_DEFERRED
#define PTHREAD_CANCEL_DEFERRED 0
#endif
#ifndef PTHREAD_CANCEL_ASYNCHRONOUS
#define PTHREAD_CANCEL_ASYNCHRONOUS 1
#endif

static inline int c10t_pthread_setcancelstate_noop(int state, int *oldstate) {
  if (oldstate) {
    *oldstate = state;
  }
  return 0;
}

static inline int c10t_pthread_setcanceltype_noop(int type, int *oldtype) {
  if (oldtype) {
    *oldtype = type;
  }
  return 0;
}

#ifdef pthread_setcancelstate
#undef pthread_setcancelstate
#endif
#ifdef pthread_setcanceltype
#undef pthread_setcanceltype
#endif
#define pthread_setcancelstate c10t_pthread_setcancelstate_noop
#define pthread_setcanceltype c10t_pthread_setcanceltype_noop
#endif
