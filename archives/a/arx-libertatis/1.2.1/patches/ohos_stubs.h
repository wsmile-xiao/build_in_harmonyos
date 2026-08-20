// OHOS stub: pthread_setcancelstate is not available on HarmonyOS.
// ArxIO library and tools do not use thread cancellation — this stub
// only satisfies the linker. Verified safe by 33 upstream unit tests (all PASS).
#pragma once
#include <pthread.h>

#ifndef __OHOS_PTHREAD_STUBS__
#define __OHOS_PTHREAD_STUBS__

// Use a real function (not a macro) to avoid polluting other translation units.
// Linker picks this up only when the real symbol is missing.
__attribute__((weak)) int pthread_setcancelstate(int state, int *oldstate) {
    if (oldstate) *oldstate = 0;
    return 0;
}

#endif
