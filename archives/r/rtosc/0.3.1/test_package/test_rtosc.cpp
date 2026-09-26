// Consumer test for rtosc/0.3.1 — exercises both packaged libraries.
//
// librtosc (C): message/bundle construction, argument query, validation,
//   version struct. librtosc-cpp (C++): Ports dispatch to a real callback.
// Each numbered scenario prints exactly one "CHECK-OK:" line on success and
// returns non-zero on the first failure, so the conanfile can count the
// lines for the HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
// A stub binary (wrong output, empty output, swallowed failure) fails loudly.
#include <cstdio>
#include <cstring>

#include <rtosc/rtosc.h>
#include <rtosc/rtosc-version.h>
#include <rtosc/ports.h>

static int g_failures = 0;

static void check(bool cond, const char *name)
{
    if (cond) {
        std::printf("CHECK-OK: %s\n", name);
    } else {
        std::printf("CHECK-FAIL: %s\n", name);
        ++g_failures;
    }
}

static int g_dispatched_int = 0;

static const rtosc::Ports g_ports = {
    {"setint:i", "", 0,
     [](rtosc::msg_t msg, rtosc::RtData &) {
         g_dispatched_int = rtosc_argument(msg, 0).i;
     }},
};

int main()
{
    char buffer[256];
    char bundle[512];

    // 1. C message build + argument count/types.
    size_t sz = rtosc_message(buffer, sizeof(buffer), "/testing", "is", 23, "this string");
    check(sz != 0 && rtosc_narguments(buffer) == 2, "c-message-nargs");
    check(rtosc_type(buffer, 0) == 'i' && rtosc_type(buffer, 1) == 's', "c-message-types");

    // 2. C argument values round-trip (int + string).
    check(rtosc_argument(buffer, 0).i == 23, "c-arg-int");
    const char *s = rtosc_argument(buffer, 1).s;
    check(s != nullptr && std::strcmp(s, "this string") == 0, "c-arg-string");

    // 3. Version struct matches the packaged 0.3.1 release.
    rtosc_version cur = rtosc_current_version();
    check(cur.major == 0 && cur.minor == 3 && cur.revision == 1, "version-is-0.3.1");
    rtosc_version older = {0, 3, 0};
    check(rtosc_version_cmp(cur, older) > 0, "version-cmp");

    // 4. Bundle round-trip with two sub-messages.
    char sub1[128], sub2[128];
    size_t s1 = rtosc_message(sub1, sizeof(sub1), "/a", "i", 1);
    size_t s2 = rtosc_message(sub2, sizeof(sub2), "/b", "i", 2);
    size_t bs = 0;
    if (s1 != 0 && s2 != 0)
        bs = rtosc_bundle(bundle, sizeof(bundle), 0, 2, sub1, sub2);
    check(bs != 0 && rtosc_bundle_p(bundle) == 1, "bundle-build");
    check(bs != 0 && rtosc_bundle_elements(bundle, sizeof(bundle)) == 2, "bundle-elements");

    // 5. Validation + pattern match on a live message.
    // NOTE: rtosc_valid_message_p(msg, len) requires len == actual message
    // length (it checks observed_length == len), so pass vsz, not the
    // buffer capacity. rtosc_match() is a non-compliant matcher: a trailing
    // "*" does NOT consume the remainder (see src/dispatch.c
    // rtosc_match_path), so use the exact path here; prefix dispatch uses a
    // trailing "/" (e.g. "blam/" matches "blam/blam" in test/patterns.c).
    size_t vsz = rtosc_message(buffer, sizeof(buffer), "/oscil/freq", "f", 440.0f);
    check(vsz != 0 && rtosc_valid_message_p(buffer, vsz), "valid-message");
    check(vsz != 0 && rtosc_match("/oscil/freq", buffer, nullptr), "pattern-match");

    // 6. C++ Ports dispatch reaches the real callback (proves rtosc-cpp link).
    // NOTE: simple Ports::dispatch(m, d) with d.loc == NULL does plain
    // rtosc_match(port.name, m) with no leading-slash stripping (only
    // base_dispatch=true strips '/'). Upstream test/headerlib.cpp therefore
    // dispatches slash-less messages ("setint") at slash-less ports
    // ("setint:i") via ThreadLink. Mirror that here: message without '/'.
    g_dispatched_int = 0;
    size_t dsz = rtosc_message(buffer, sizeof(buffer), "setint", "i", 123);
    bool dispatched = false;
    if (dsz != 0) {
        rtosc::RtData d;
        d.loc_size = 0;
        d.obj = nullptr;
        d.loc = nullptr;
        g_ports.dispatch(buffer, d);
        dispatched = (g_dispatched_int == 123);
    }
    check(dispatched, "cpp-ports-dispatch");

    if (g_failures != 0) {
        std::printf("RESULT: %d check(s) failed\n", g_failures);
        return 1;
    }
    std::printf("RESULT: all 11 checks passed\n");
    return 0;
}
