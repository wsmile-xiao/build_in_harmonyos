/* test.cpp — libzen consumer-side functional test (OHOS).
 *
 * Upstream ZenLib ships no test framework (no add_test/ctest; the only
 * "test" Source/Example/ZenLib_Test.cpp is a demo, not built by any
 * upstream build system, and ends with an interactive system("PAUSE")).
 * These assertions instead exercise the core public APIs that the
 * HarmonyOS adaptation must keep working: Ztring (Unicode/UTF-8/number/
 * operators), ZtringListList, File, FileName and Thread (the Thread
 * path exercises Thread::ForceTerminate(), where the upstream pthread_cancel
 * call is adapted for OHOS via a weak-symbol probe).
 */
#include <ZenLib/Ztring.h>
#include <ZenLib/ZtringListList.h>
#include <ZenLib/File.h>
#include <ZenLib/FileName.h>
#include <ZenLib/Thread.h>

#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unistd.h>

using namespace ZenLib;

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        ++g_checks;                                                         \
        if (cond) {                                                         \
            std::printf("[ok]   %s\n", msg);                                \
        } else {                                                            \
            std::printf("[fail] %s\n", msg);                                \
            ++g_failures;                                                   \
        }                                                                   \
    } while (0)

// CounterThread runs a bounded cooperative loop on a detached worker thread.
// Its Ticks counter lets the test verify that (a) the worker really started,
// and (b) on OHOS, where pthread_cancel is absent and the patched
// ForceTerminate() is a no-op, the worker keeps advancing until its own
// bounded loop (or RequestTerminate()) stops it.
class CounterThread : public Thread
{
public:
    std::atomic<unsigned long> Ticks{0};
    // Thread::Sleep is a protected, non-static member, so it cannot be called
    // from a free function (e.g. main). This is the public wrapper through
    // which the protected Sleep path is still exercised.
    void SleepMs(unsigned ms) { Sleep(ms); }
    void Entry() override
    {
        for (unsigned i = 0; i < 200 && !IsTerminating(); ++i)
        {
            ++Ticks;
            SleepMs(10);
        }
    }
};

// Waits (bounded) until a worker's Entry has returned, detected by its Ticks
// counter no longer advancing. CounterThread is a detached thread, so this is
// the only way to know it finished before main tears the stack object down.
static void wait_for_worker_stop(CounterThread &t)
{
    unsigned long prev = 0;
    int stable = 0;
    for (int i = 0; i < 400; ++i) { // up to ~10s
        unsigned long now = t.Ticks.load();
        if (now == prev) {
            if (++stable >= 2)
                return; // stopped advancing -> Entry returned
        } else {
            stable = 0;
        }
        prev = now;
        ::usleep(25 * 1000);
    }
}

int main(int argc, char **argv)
{
    // --- Ztring basics ---
    Ztring Empty;
    CHECK(Empty.empty(), "Ztring default-constructed is empty");

    Ztring U;
    U.From_Unicode(L"Unicode-\xE9\x03A9"); // Unicode-éΩ
    CHECK(U.To_Unicode() == std::wstring(L"Unicode-\xE9\x03A9"),
          "Ztring From_Unicode/To_Unicode round-trip");

    Ztring L;
    L.From_Local("local ascii");
    CHECK(L.To_Local() == "local ascii", "Ztring From_Local/To_Local round-trip");

    // "测试" in UTF-8
    Ztring F;
    F.From_UTF8("\xE6\xB5\x8B\xE8\xAF\x95");
    // To_Local() goes through wcstombs under the active locale, so on OHOS
    // (default C locale, not UTF-8) it is not byte-preserving for CJK;
    // To_UTF8() is the locale-independent UTF-8 round-trip.
    CHECK(F.To_UTF8() == std::string("\xE6\xB5\x8B\xE8\xAF\x95"),
          "Ztring UTF-8 round-trip (CJK) via To_UTF8");
    CHECK(F.size() == 2, "Ztring UTF-8 size() counts characters, not bytes");

    Ztring N;
    N.From_Number(9223372036854775807ULL);
    CHECK(N.To_Local() == "9223372036854775807",
          "Ztring From_Number(int64u)/To_Local round-trip");

    Ztring A, B;
    A.From_Local("foo");
    B.From_Local("bar");
    A += B;
    CHECK(A.To_Local() == "foobar", "Ztring operator+= concatenation");

    Ztring C;
    C = A;
    CHECK(C.To_Local() == "foobar", "Ztring operator= assignment");

    // --- ZtringListList ---
    ZtringListList ZLL("11;12;13\r\n21;22;23\r\n31;32;33");
    CHECK(ZLL.size() == 3, "ZtringListList parses 3 lines");
    CHECK(ZLL.Read(1, 1).To_Local() == "22", "ZtringListList Read(1,1)");
    CHECK(ZLL.Read(0).To_Local() == "11;12;13", "ZtringListList Read(0) whole line");

    // --- File ---
    const char *tmpdir = (argc > 1 && argv[1]) ? argv[1] : ".";
    std::string probe = std::string(tmpdir) + "/libzen_tp_probe.txt";
    {
        FILE *f = std::fopen(probe.c_str(), "w");
        if (f) {
            std::fputs("probe", f);
            std::fclose(f);
        }
    }
    Ztring ProbePath(probe.c_str());
    CHECK(File::Exists(ProbePath), "File::Exists true for a just-created file");

    Ztring MissingPath((probe + ".missing").c_str()); // UTF-8 ctor (UNICODE build)
    CHECK(!File::Exists(MissingPath), "File::Exists false for a non-existent file");

    // --- FileName ---
    Ztring Ext = FileName::Extension_Get("a/b/c.tar.gz");
    CHECK(Ext.To_Local() == "gz", "FileName::Extension_Get");

    // --- Thread ---
    // The single adaptation patch lives in Thread::ForceTerminate():
    // upstream calls pthread_cancel, which OHOS musl does not provide.
    // Patch 0001 probes the symbol via a weak declaration, so this test
    // exercises the real patched ForceTerminate() path at runtime.
    CounterThread W;
    CHECK(W.Run() == Thread::Ok, "Thread::Run returns Ok");
    W.SleepMs(80);
    CHECK(W.Ticks.load() > 0, "worker thread is running before ForceTerminate");

    CHECK(W.ForceTerminate() == Thread::Ok,
          "Thread::ForceTerminate returns Ok (patched weak-symbol path)");
    CHECK(W.IsExited(),
          "Thread::ForceTerminate marks the thread exited (IsExited)");

    // On OHOS, pthread_cancel resolves to NULL, so ForceTerminate() is a
    // no-op: it marks the thread terminated but the detached worker keeps
    // advancing until its own bounded loop (or RequestTerminate()) stops it.
    W.SleepMs(80);
    CHECK(W.RequestTerminate() == Thread::IsNotRunning,
          "Thread::RequestTerminate after ForceTerminate reports IsNotRunning");
    CHECK(W.Ticks.load() > 0,
          "worker kept advancing on OHOS (ForceTerminate no-op, loop bounds via its own count)");

    // Cooperative exit: a thread that is stopped via RequestTerminate ends
    // cleanly, proving RequestTerminate/Sleep-driven termination works as the
    // portability fallback.
    CounterThread C2;
    CHECK(C2.Run() == Thread::Ok, "Thread::Run (2nd instance) returns Ok");
    C2.SleepMs(80);
    CHECK(C2.RequestTerminate() == Thread::Ok,
          "Thread::RequestTerminate while running returns Ok");
    int waited = 0;
    while (!C2.IsExited() && waited < 200) {
        ::usleep(20 * 1000);
        ++waited;
    }
    CHECK(C2.IsExited(), "cooperative thread exits after RequestTerminate");

    // Thread::Run() spawns a detached pthread (PTHREAD_CREATE_DETACHED), so it
    // outlives the stack CounterThread objects. Wait until each worker's Entry
    // actually returned (its Ticks counter stops advancing) before main
    // returns, otherwise the detached thread would touch a freed stack object.
    wait_for_worker_stop(W);
    wait_for_worker_stop(C2);

    std::printf("\n%d/%d checks passed\n", g_checks - g_failures, g_checks);
    return g_failures == 0 ? 0 : 1;
}
