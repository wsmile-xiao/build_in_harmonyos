// test_tracy.cpp — consumer-side verification of the Tracy client library.
//
// The default Tracy build (TRACY_DELAYED_INIT off) initialises the client during
// static initialisation, and the manual-lifetime entry points
// (___tracy_startup_profiler & friends) are only declared when
// TRACY_MANUAL_LIFETIME is defined (TracyC.h:207-215). This test therefore
// drives the always-available public API and asserts three properties that a
// broken package would fail:
//   1. the header is in its "enabled" branch (TracyCIsStarted == 1) — without the
//      exported TRACY_ENABLE definition the whole API degrades to no-op macros;
//   2. a source location can be allocated;
//   3. a zone begin/name/end round trip returns a live (non-zero) zone id.
// The connection-state query is only reported as information: upstream returns
// (int32_t)IsConnected(), so asserting on it would have no discriminating power.
#include <cstdio>
#include <cstring>

#include <tracy/TracyC.h>

static int failures = 0;

static void check(bool cond, const char* what)
{
    if (cond) {
        std::printf("[ ok ] %s\n", what);
    } else {
        std::fprintf(stderr, "[FAIL] %s\n", what);
        ++failures;
    }
}

int main()
{
    // In the default build TracyCIsStarted expands to the literal 1; a build
    // without TRACY_ENABLE would make every other call below a no-op macro.
    check(TracyCIsStarted == 1, "TRACY_ENABLE is visible to the consumer (TracyCIsStarted == 1)");

    const char* source = "test_tracy.cpp";
    const char* function = "main";
    const uint64_t srcloc = ___tracy_alloc_srcloc(
        __LINE__, source, std::strlen(source), function, std::strlen(function), 0);
    check(srcloc != 0, "___tracy_alloc_srcloc() returns a usable source location");

    const TracyCZoneCtx zone = ___tracy_emit_zone_begin_alloc(srcloc, 1);
    check(zone.id != 0, "___tracy_emit_zone_begin_alloc() returns a live zone id");
    ___tracy_emit_zone_name(zone, "tracy-ci-zone", std::strlen("tracy-ci-zone"));
    ___tracy_emit_zone_end(zone);

    ___tracy_set_thread_name("tracy-test");

    std::printf("[info] zone id=%u active=%d\n", (unsigned)zone.id, (int)zone.active);
    std::printf("[info] profiler server connected: %s\n",
                ___tracy_connected() ? "yes" : "no (expected without a Tracy server)");

    if (failures != 0) {
        std::fprintf(stderr, "test_tracy: %d check(s) failed\n", failures);
        return 1;
    }
    std::printf("test_tracy: all 3 checks passed\n");
    return 0;
}
