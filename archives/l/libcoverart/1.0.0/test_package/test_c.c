/* Consumer test for the libcoverart C API (offline).
 *
 * Exercises object lifecycle, version query, proxy setters and the
 * last-result/last-http-code/last-error accessors without any network
 * traffic. Each CHECK prints exactly one PASS: or FAIL: line.
 */
#include <stdio.h>
#include <string.h>

#include "coverart/caa_c.h"

static int passed = 0;
static int failed = 0;

#define CHECK(cond, label) do { \
    if (cond) { printf("PASS: %s\n", label); passed++; } \
    else { printf("FAIL: %s\n", label); failed++; } } while (0)

int main(void)
{
    char buf[256];
    CaaCoverArt ca;
    CaaCoverArt clone;

    ca = caa_coverart_new("hmbs-test-1.0");
    CHECK(ca != 0, "caa_coverart_new returns non-NULL");
    if (!ca) {
        printf("RESULT: %d passed, %d failed\n", passed, failed);
        return 1;
    }

    buf[0] = '\0';
    caa_coverart_get_version(ca, buf, sizeof(buf));
    CHECK(buf[0] != '\0', "caa_coverart_get_version returns non-empty string");
    CHECK(strstr(buf, "1.0.0") != NULL, "caa_coverart_get_version mentions 1.0.0");

    /* Proxy setters are pure local state; they must not crash and must not
     * disturb the pre-fetch result state. */
    caa_coverart_set_proxyhost(ca, "proxy.example");
    caa_coverart_set_proxyport(ca, 8080);
    caa_coverart_set_proxyusername(ca, "user");
    caa_coverart_set_proxypassword(ca, "secret");
    CHECK(caa_coverart_get_lastresult(ca) == eCoverArt_Success,
          "lastresult is eCoverArt_Success before any fetch");
    CHECK(caa_coverart_get_lasthttpcode(ca) == 200,
          "lasthttpcode is 200 before any fetch");
    buf[0] = 'X';
    caa_coverart_get_lasterrormessage(ca, buf, sizeof(buf));
    CHECK(buf[0] == '\0', "lasterrormessage is empty before any fetch");

    clone = caa_coverart_clone(ca);
    CHECK(clone != 0, "caa_coverart_clone returns non-NULL");
    caa_coverart_delete(clone);
    caa_coverart_delete(ca);
    CHECK(1, "caa_coverart_delete completes without crash");

    printf("RESULT: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
