/* Conan consumer test for libnpupnp 6.2.3 (HarmonyOS aarch64).
 *
 * Exercises the real public API the same way the upstream test programs do:
 *   - version consistency (mirrors test/test_init.cpp version checks)
 *   - URL resolution via UpnpResolveURL2 (mirrors test/test_url.cpp cases,
 *     RFC 3986 normal/abnormal examples plus the error paths)
 *   - library init/finish via UpnpInit/UpnpFinish (mirrors test_init.cpp)
 *
 * Every CHECK counts as one assertion. The summary line and the
 * HMBS_TEST_PACKAGE_RESULT marker use the same counters, exit 0 only when
 * every check passes so a regression fails the conan test phase instead of
 * passing silently.
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "upnp.h"
#include "upnptools.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            ++g_failed;                                                        \
            std::printf("FAIL line %d: %s\n", __LINE__, #cond);                 \
        } else {                                                               \
            std::printf("ok line %d: %s\n", __LINE__, #cond);                   \
        }                                                                      \
    } while (0)

static int check_resolve(const char *base, const char *rel,
                         const char *expected, int expected_ret) {
    char *absurl = NULL;
    int rc = UpnpResolveURL2(base, rel, &absurl);
    int ok = (rc == expected_ret);
    if (ok && expected != NULL) {
        ok = (absurl != NULL && std::strcmp(absurl, expected) == 0);
    }
    ++g_checks;
    if (!ok) {
        ++g_failed;
        std::printf("FAIL resolve: base='%s' rel='%s' -> '%s' (expected '%s', rc=%d want %d)\n",
                    base ? base : "(null)", rel ? rel : "(null)",
                    absurl ? absurl : "(null)",
                    expected ? expected : "(null)", rc, expected_ret);
    } else {
        std::printf("ok resolve: base='%s' rel='%s' -> '%s'\n",
                    base ? base : "(null)", rel ? rel : "(null)",
                    absurl ? absurl : "(null)");
    }
    std::free(absurl);
    return ok ? 0 : 1;
}

int main(void) {
    std::printf("=== libnpupnp 6.2.3 consumer test (HarmonyOS/aarch64) ===\n");

    /* 1. Version consistency, mirrors test_init.cpp. */
    std::printf("--- version (test_init equivalent) ---\n");
    int major = 0, minor = 0, patch = 0;
    CHECK(std::sscanf(NPUPNP_VERSION_STRING, "%d.%d.%d", &major, &minor,
                      &patch) == 3);
    CHECK(major == NPUPNP_VERSION_MAJOR && major == 6);
    CHECK(minor == NPUPNP_VERSION_MINOR && minor == 2);
    CHECK(patch == NPUPNP_VERSION_PATCH && patch == 3);

    /* 2. URL resolution, mirrors test_url.cpp (RFC 3986 cases). */
    std::printf("--- UpnpResolveURL2 (test_url equivalent) ---\n");
    const char *base1 = "http://pupnp.sourceforge.net/path1/";
    const char *base2 = "http://pupnp.sourceforge.net/path1/path1";
    const char *abs2 = "http://pupnp.sourceforge.net/path1/path1";
    const char *rfc = "http://localhost/b/c/d;p?q";
    check_resolve(NULL, NULL, NULL, UPNP_E_INVALID_PARAM);
    check_resolve(base1, NULL, NULL, UPNP_E_INVALID_PARAM);
    check_resolve("foo", "bar", NULL, UPNP_E_INVALID_URL);
    check_resolve(base1, abs2, abs2, UPNP_E_SUCCESS);
    check_resolve(base1, "path4", "http://pupnp.sourceforge.net/path1/path4",
                  UPNP_E_SUCCESS);
    check_resolve(base2, "../path5", "http://pupnp.sourceforge.net/path5",
                  UPNP_E_SUCCESS);
    check_resolve(base1, "#frag1",
                  "http://pupnp.sourceforge.net/path1/#frag1", UPNP_E_SUCCESS);
    check_resolve(rfc, "g", "http://localhost/b/c/g", UPNP_E_SUCCESS);
    check_resolve(rfc, "../g", "http://localhost/b/g", UPNP_E_SUCCESS);
    check_resolve(rfc, "g/../h", "http://localhost/b/c/h", UPNP_E_SUCCESS);

    /* 3. Library init/finish, mirrors test_init.cpp. */
    std::printf("--- UpnpInit/UpnpFinish (test_init equivalent) ---\n");
    int rc = UpnpInit(NULL, 0);
    CHECK(rc == UPNP_E_SUCCESS);
    if (rc == UPNP_E_SUCCESS) {
        const char *ip = UpnpGetServerIpAddress();
        unsigned short port = UpnpGetServerPort();
        std::printf("UpnpInit OK ip=%s port=%u\n", ip ? ip : "UNKNOWN", port);
        CHECK(ip != NULL);
        CHECK(port != 0);
        CHECK(UpnpFinish() == UPNP_E_SUCCESS);
    } else {
        std::printf("UpnpInit failed rc=%d\n", rc);
    }

    int passed = g_checks - g_failed;
    std::printf("\n=== Results: %d/%d passed, %d failed ===\n", passed,
                g_checks, g_failed);
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
                "\"command\":\"test_npupnp\",\"discovered\":%d,"
                "\"passedCount\":%d}\n",
                g_failed == 0 ? "true" : "false", g_checks, passed);
    if (g_failed == 0) {
        std::printf("libnpupnp consumer checks PASSED.\n");
        return 0;
    }
    std::printf("libnpupnp consumer checks FAILED.\n");
    return 1;
}
