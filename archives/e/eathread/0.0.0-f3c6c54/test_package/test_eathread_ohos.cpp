// test_eathread_ohos.cpp — HarmonyOS-specific test for EAThread.
//
// Distinct from the upstream suite and from the generic consumer test: it
// exercises EAThread behaviors that the OHOS musl port touches directly —
//   (1) thread creation/join + mutex/semaphore cross-thread handshake,
//   (2) Barrier construction (compiled without pthread_setcancelstate on
//       OHOS),
//   (3) thread affinity mask path (guarded to syscall sched_setaffinity on
//       OHOS; must not crash),
//   (4) portable callstack walk (must not crash on OHOS).
// Asserts observable results; a no-op build cannot pass.

#include <eathread/eathread.h>
#include <eathread/eathread_mutex.h>
#include <eathread/eathread_semaphore.h>
#include <eathread/eathread_thread.h>
#include <eathread/eathread_barrier.h>
#include <eathread/eathread_callstack.h>

#include <cstdio>

namespace Thread = EA::Thread;

static int gHandshake = 0;
static Thread::Mutex gMutex(NULL, true);
static Thread::Semaphore gSemaphore(0);

static intptr_t OHOSWorker(void* /*pContext*/)
{
    gSemaphore.Wait();
    {
        Thread::AutoMutex lock(gMutex);
        gHandshake++;
    }
    return 0;
}

int main()
{
    int failures = 0;

    // 1) Thread create/join round-trip with mutex+semaphore (OHOS pthread backend).
    Thread::Thread t;
    t.Begin(OHOSWorker, NULL);
    gSemaphore.Post();
    t.WaitForEnd();
    if (gHandshake != 1) {
        std::printf("FAIL: handshake=%d expected 1\n", gHandshake);
        failures++;
    }

    // 2) Barrier path (compiled without pthread_setcancelstate on OHOS).
    {
        Thread::Barrier barrier(2);
        std::printf("barrier constructed ok\n");
    }

    // 3) Thread affinity mask set must not crash on OHOS (guarded impl):
    //    SetCurrentThreadAffinityMask falls into the other-Unix no-op branch
    //    (patch 0004) and Thread affinity uses syscall sched_setaffinity
    //    (patch 0003); both must run without crashing on OHOS.
    {
        Thread::SetThreadAffinityMask(Thread::kThreadAffinityMaskAny);
        Thread::Thread aff;
        aff.Begin(OHOSWorker, NULL);
        gSemaphore.Post();
        aff.SetAffinityMask(Thread::kThreadAffinityMaskAny);
        aff.WaitForEnd();
        std::printf("affinity path ok\n");
    }

    // 4) Callstack walk must return without crashing on OHOS.
    {
        void* frames[8];
        const size_t n = Thread::GetCallstack(frames, 8);
        std::printf("callstack frames=%zu\n", n);
        if (n == 0) {
            std::printf("FAIL: callstack returned 0 frames\n");
            failures++;
        }
    }

    if (failures == 0) {
        std::printf("test_eathread_ohos: OK\n");
        return 0;
    }
    std::printf("test_eathread_ohos: %d failure(s)\n", failures);
    return 1;
}
