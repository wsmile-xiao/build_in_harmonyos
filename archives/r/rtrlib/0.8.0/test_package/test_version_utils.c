/* Consumer test for rtrlib: version macros and IP address helpers. */
#include <stdio.h>
#include <string.h>

#include <netinet/in.h>

#include <rtrlib/rtrlib.h>

#include <stdbool.h>

/* Upstream contract guards (rtrlib 0.8.0, rtrlib/lib/ip.h):
 * lrtr_ip_addr_equal() takes the structs by value, and
 * lrtr_ip_str_cmp() takes 2 args and returns true on match.
 * Any upstream signature change stops compilation here with an
 * explicit message instead of a cryptic call-site error.
 * Compile-time only: CHECK count and runtime behaviour unchanged.
 * Provenance (checked against the exact conandata tarball v0.8.0,
 * 262281 bytes, sha256 8cc99343...560ada): ip.h L75 declares equal
 * by value, L84 declares 2-arg bool str_cmp; upstream
 * tests/test_ipaddr.c L235-244 calls equal by value. */
_Static_assert(__builtin_types_compatible_p(__typeof__(lrtr_ip_addr_equal),
    bool (const struct lrtr_ip_addr, const struct lrtr_ip_addr)),
    "lrtr_ip_addr_equal must take lrtr_ip_addr by value");
_Static_assert(__builtin_types_compatible_p(__typeof__(lrtr_ip_str_cmp),
    bool (const struct lrtr_ip_addr *, const char *)),
    "lrtr_ip_str_cmp must be the 2-arg bool 0.8.0 form");

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);            \
            return 1;                                                          \
        }                                                                      \
        printf("ok: %s\n", msg);                                               \
    } while (0)

int main(void)
{
    char buf[INET6_ADDRSTRLEN];
    struct lrtr_ip_addr a;
    struct lrtr_ip_addr b;

    CHECK(RTRLIB_VERSION_MAJOR == 0 && RTRLIB_VERSION_MINOR == 8 &&
          RTRLIB_VERSION_PATCH == 0, "version macros report 0.8.0");

    CHECK(lrtr_ip_str_to_addr("10.0.0.1", &a) == 0, "parse IPv4 address");
    CHECK(a.ver == LRTR_IPV4, "parsed address is IPv4");
    CHECK(lrtr_ip_addr_to_str(&a, buf, sizeof(buf)) == 0, "format IPv4 address");
    CHECK(strcmp(buf, "10.0.0.1") == 0, "IPv4 address round-trips");

    CHECK(lrtr_ip_str_to_addr("10.0.0.1", &b) == 0, "re-parse IPv4 address");
    CHECK(lrtr_ip_addr_equal(a, b), "equal addresses compare equal");
    CHECK(lrtr_ip_str_cmp(&a, "10.0.0.1"), "string comparison matches");

    CHECK(lrtr_ip_str_to_addr("2001:db8::1", &b) == 0, "parse IPv6 address");
    CHECK(b.ver == LRTR_IPV6, "parsed address is IPv6");
    CHECK(!lrtr_ip_addr_equal(a, b), "IPv4 and IPv6 compare unequal");

    printf("test_version_utils: ALL OK\n");
    return 0;
}
