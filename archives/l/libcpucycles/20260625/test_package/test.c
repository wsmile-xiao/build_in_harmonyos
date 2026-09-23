// test_package for libcpucycles 20260625 — consumer-side API contract test.
//
// Contract source (upstream doc/man/cpucycles.3, cpucycles/wrapper.c):
//   - cpucycles() is a function POINTER; first call selects a counter and
//     rewrites the pointer. Subsequent calls must not re-init.
//   - cpucycles() returns an ESTIMATE of cycles since an unspecified epoch;
//     accuracy is best-effort; a low-precision counter is acceptable
//     (upstream explicitly allows selecting a low-precision counter).
//   - cpucycles_persecond() returns an estimate of cycles per second.
//     Guaranteed POSITIVE: osfreq() always returns > 0 (hardcoded fallback
//     2399987654.0 is the last resort). The value is computed ONCE at init
//     (wrapper.c: persecond = osfreq() inside cpucycles_init), so repeated
//     calls after init return the same number.
//   - cpucycles_implementation() returns the counter name in use,
//     non-NULL, stable across calls (implementation is a static const char*).
//   - cpucycles_version() returns the version string "20260625".
//   - cpucycles_tracesetup() only sets a static flag consumed during init;
//     after init it has no effect on reads (wrapper.c:35-40).
//
// What is deliberately NOT asserted (not guaranteed by the API):
//   - exact cycle deltas between two reads (machine performance)
//   - persecond being the true CPU frequency, or numerically consistent
//     with the selected counter's tick rate
//   - which backend gets selected (runtime environment decides)
//   - monotonicity ACROSS a sleep/context switch: real cycle counters
//     (e.g. arm64-pmc reading PMCCNTR_EL0) are PER-CORE, and the upstream
//     selection loop itself notes "!ok can be caused by overflow or by
//     core swap" (wrapper.c). A thread migrated to another core observes
//     an arbitrary counter offset. Observed on OHOS: reading across a
//     50ms nanosleep returned ~51% of the pre-sleep value. Therefore all
//     read-to-read assertions are confined to consecutive tight-loop
//     reads — the exact criterion the upstream selection loop itself
//     uses to accept a backend (non-decreasing over CALLS calls).

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include <cpucycles.h>

#define CHECK(cond, name, fmt, args...) do {                        \
    int _ok = (cond) ? 1 : 0;                                       \
    printf("[%s] %s: " fmt "\n", _ok ? "PASS" : "FAIL", name, ##args); \
    if (!_ok) ret = 1;                                              \
} while (0)

int main(void)
{
    int ret = 0;

    /* 1. version string: upstream hardcodes "20260625" (wrapper.c) */
    const char *ver = cpucycles_version();
    CHECK(strcmp(ver, "20260625") == 0, "version",
          "cpucycles_version() == \"20260625\" (got \"%s\")", ver);

    /* 2. lazy init via first cpucycles() call: returns an estimate,
     *    no error path documented — any value is acceptable here,
     *    validity is established by the checks below */
    long long c1 = cpucycles();
    printf("[INFO] first cpucycles() = %" PRId64 "\n", (int64_t) c1);

    /* 3. implementation: non-NULL, non-empty, stable across calls */
    const char *impl1 = cpucycles_implementation();
    const char *impl2 = cpucycles_implementation();
    CHECK(impl1 != NULL && impl1[0] != '\0', "implementation-nonnull",
          "implementation = \"%s\"", impl1 ? impl1 : "(NULL)");
    CHECK(impl1 == impl2, "implementation-stable",
          "same static pointer returned twice (%p == %p)", (void *) impl1, (void *) impl2);

    /* implementation must be one of the compiled-in backends
     * (options.inc for aarch64 OHOS build: 8 options) */
    const char *known_impls[] = {
        "arm64-perfpmc", "arm64-pmc", "arm64-vct",
        "default-perfevent", "default-mach", "default-monotonic",
        "default-gettimeofday", "default-zero",
    };
    int impl_known = 0;
    for (size_t i = 0; i < sizeof(known_impls) / sizeof(known_impls[0]); ++i)
        if (strcmp(impl1, known_impls[i]) == 0) { impl_known = 1; break; }
    CHECK(impl_known, "implementation-known",
          "\"%s\" is one of the 8 options.inc backends", impl1);

    /* 4. persecond: positive estimate (osfreq() always > 0) */
    long long ps = cpucycles_persecond();
    CHECK(ps > 0, "persecond-positive",
          "cpucycles_persecond() = %" PRId64 " (> 0)", (int64_t) ps);

    /* 5. counter is not fake zero data: the default-zero fallback returns
     *    constant 0; upstream only picks it when everything else fails.
     *    On a real OHOS AArch64 device monotonic/gettimeofday must work,
     *    so a constant-0 counter would mean the selection is broken.
     *    NOTE: we assert non-decreasing + at least one STRICT increase
     *    over enough reads, matching the upstream selection loop's own
     *    acceptance criterion (t[0] != t[CALLS] after <=1000 calls). */
    long long first = cpucycles();
    long long maxv = first;
    int increased = 0;
    for (int i = 0; i < 1000; ++i) {
        long long v = cpucycles();
        if (v > maxv) { increased = 1; maxv = v; }
    }
    CHECK(maxv > first, "counter-increases",
          "at least one strict increase over 1000 reads (first=%" PRId64
          ", max=%" PRId64 ")", (int64_t) first, (int64_t) maxv);

    /* 6. monotonicity within a single-threaded tight loop: the upstream
     *    selection itself accepts t[i] <= t[i+1] over 1000 calls, so we
     *    hold the test to the same standard (allow equal, forbid
     *    strictly decreasing). */
    long long prev = cpucycles();
    int monotonic = 1;
    for (int i = 0; i < 1000; ++i) {
        long long v = cpucycles();
        if (v < prev) { monotonic = 0; break; }
        prev = v;
    }
    CHECK(monotonic, "counter-monotonic",
          "non-decreasing over 1000 consecutive reads (allow equal)");

    /* 7. persecond is stable across calls after init: wrapper.c computes
     * persecond = osfreq() exactly once inside cpucycles_init() and stores
     * it in a static; every subsequent cpucycles_persecond() returns that
     * cached value. A different value would mean the pointer was reset to
     * cpucycles_init (re-init), which the API documents against. */
    {
        long long ps2 = cpucycles_persecond();
        long long ps3 = cpucycles_persecond();
        CHECK(ps2 == ps && ps3 == ps, "persecond-stable",
              "cpucycles_persecond() stable after init (%" PRId64
              " == %" PRId64 " == %" PRId64 ")", (int64_t) ps2, (int64_t) ps3, (int64_t) ps);
    }

    /* 8. persecond plausible range: the man page calls it "an estimate for
     * the number of CPU cycles per second" — i.e. a CPU frequency. Any
     * real CPU frequency lies in [1e6, 1e12]; a value outside that range
     * would mean osfreq() misparsed a source and returned garbage. This
     * is deliberately wide (6 orders of magnitude) so it never depends on
     * machine performance. */
    {
        int plausible = (ps >= 1000000LL && ps <= 1000000000000LL);
        CHECK(plausible, "persecond-plausible",
              "cpucycles_persecond() = %" PRId64 " in [1e6, 1e12]", (int64_t) ps);
    }

    /* 9. tracesetup: upstream public API. Calling it after init must not
     * crash, must not disturb the selected counter (it only sets a static
     * flag consumed during init — wrapper.c:35-40), and must not re-select
     * a backend (implementation unchanged, persecond unchanged). The read
     * after tracesetup() is checked within the same tight sequence, NOT
     * against the pre-sleep maxv: per-core counters legitimately shift on
     * core migration (see header comment). */
    cpucycles_tracesetup();
    {
        const char *impl3 = cpucycles_implementation();
        long long ps4 = cpucycles_persecond();
        long long a = cpucycles();
        long long b = cpucycles();
        CHECK(impl3 == impl1 && ps4 == ps && b >= a, "tracesetup-noop-after-init",
              "after tracesetup(): impl stable (%s), persecond stable (%" PRId64
              "), counter non-decreasing (%" PRId64 " >= %" PRId64 ")",
              impl3, (int64_t) ps4, (int64_t) b, (int64_t) a);
    }

    printf("test libcpucycles API: %s (implementation=%s, version=%s)\n",
           ret ? "FAIL" : "OK", impl1, ver);
    return ret;
}
