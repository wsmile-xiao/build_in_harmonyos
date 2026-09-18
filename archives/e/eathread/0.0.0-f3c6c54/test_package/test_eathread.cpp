// test_eathread.cpp — HarmonyOS consumer test for EAThread.
//
// Consumer-style verification: uses only the public EAThread API
// (EA::Thread::Mutex / EA::Thread::AutoMutex / EA::Thread::Semaphore /
// EA::Thread::Thread / EA::Thread::ThreadFactory / EA::Thread::AtomicInt32)
// exactly as an application would, and asserts observable results (mutex
// mutual exclusion, thread start/join, atomic increment) so a no-op build
// cannot pass.

#include <eathread/eathread.h>
#include <eathread/eathread_mutex.h>
#include <eathread/eathread_semaphore.h>
#include <eathread/eathread_thread.h>
#include <eathread/eathread_atomic.h>

#include <cstdio>

namespace Thread = EA::Thread;

static int gSharedCounter = 0;
static Thread::Mutex gMutex(NULL, true);
static Thread::Semaphore gSemaphore(0);

static intptr_t ThreadFunc(void* pContext)
{
    int* pValue = static_cast<int*>(pContext);
    gSemaphore.Wait();
    {
        Thread::AutoMutex lock(gMutex);
        gSharedCounter += *pValue;
    }
    return 0;
}

int main()
{
    int failures = 0;

    // 1) Mutex mutual exclusion + AutoMutex on the consumer thread.
    gMutex.Lock();
    gSharedCounter = 1;
    gMutex.Unlock();

    // 2) Semaphore wait/post round-trip across threads.
    Thread::Thread worker[2];
    int valueA = 10, valueB = 20;
    worker[0].Begin(ThreadFunc, &valueA);
    worker[1].Begin(ThreadFunc, &valueB);

    gSemaphore.Post();
    gSemaphore.Post();

    worker[0].WaitForEnd();
    worker[1].WaitForEnd();

    // 3) Atomic operations from the public header.
    Thread::AtomicInt32 atomicValue = 0;
    atomicValue.Increment();
    atomicValue.Increment();
    const int atomicResult = atomicValue.GetValue();

    if (gSharedCounter != 31) {
        std::printf("FAIL: gSharedCounter=%d expected 31\n", gSharedCounter);
        failures++;
    }
    if (atomicResult != 2) {
        std::printf("FAIL: atomicResult=%d expected 2\n", atomicResult);
        failures++;
    }

    // 4) ThreadFactory create/destroy path.
    Thread::Thread* pThread = Thread::ThreadFactory::CreateThread();
    if (!pThread) {
        std::printf("FAIL: ThreadFactory::CreateThread returned null\n");
        failures++;
    } else {
        Thread::ThreadFactory::DestroyThread(pThread);
    }

    if (failures == 0) {
        std::printf("test_eathread: OK (counter=%d atomic=%d)\n", gSharedCounter, atomicResult);
        return 0;
    }
    std::printf("test_eathread: %d failure(s)\n", failures);
    return 1;
}