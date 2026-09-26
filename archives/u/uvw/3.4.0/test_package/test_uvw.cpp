// test_uvw.cpp — uvw 3.4.0 consumer test (R34: real API usage).
//
// Drives a real libuv event loop through the uvw C++ facade: creates a loop,
// arms a one-shot 5ms timer, runs the loop, and verifies the callback fired
// exactly once and the loop drained. Also probes the underlying libuv runtime
// version to prove the transitive libuv linkage is functional. Four
// "CASE PASS" assertions; any failure prints "CASE FAIL" and exits non-zero.
// test_package/conanfile.py counts the CASE PASS lines for the
// HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
#include <cstdio>

#include <uvw.hpp>
#include <uv.h>

int main() {
    // CHECK 1: underlying libuv runtime is really linked.
    const char *ver = uv_version_string();
    if (ver != nullptr && uv_version() >= 0x010000) {
        std::printf("CASE PASS libuv-version %s\n", ver);
    } else {
        std::printf("CASE FAIL libuv-version\n");
        return 1;
    }

    // CHECK 2: uvw loop facade is usable.
    auto loop = uvw::loop::create();
    if (loop) {
        std::printf("CASE PASS loop-create\n");
    } else {
        std::printf("CASE FAIL loop-create\n");
        return 1;
    }

    // CHECK 3: a real timer round-trip through loop->run().
    auto timer = loop->resource<uvw::timer_handle>();
    int fired = 0;
    timer->on<uvw::timer_event>(
        [&fired](const uvw::timer_event &, uvw::timer_handle &) { ++fired; });
    timer->start(uvw::timer_handle::time{5}, uvw::timer_handle::time{0});
    loop->run();
    if (fired == 1) {
        std::printf("CASE PASS timer-fired-once\n");
    } else {
        std::printf("CASE FAIL timer-fired-once fired=%d\n", fired);
        return 1;
    }

    // CHECK 4: the loop drained normally after run().
    if (!loop->alive()) {
        std::printf("CASE PASS loop-drained\n");
    } else {
        std::printf("CASE FAIL loop-drained\n");
        return 1;
    }

    std::printf("ALL PASS\n");
    return 0;
}
