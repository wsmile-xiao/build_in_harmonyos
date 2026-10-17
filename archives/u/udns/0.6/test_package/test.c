/* test_udns.c — Conan test_package consumer test for libudns (udns 0.6).
 *
 * Substantive verification (R34): calls the real udns API across several
 * independent, offline-deterministic areas:
 *   1. dns_init(NULL, 0)  — initialize resolver context (do_open=0: no network
 *      socket opened, safe in sandboxed/offline environments).
 *   2. dns_version()      — returns the library version string.
 *   3. Domain-name (DN) wire round-trip: dns_sptodn() -> dns_dntosp() and
 *      dns_dnlen()/dns_dnequal() to prove label parsing is functional.
 *   4. IP address conversion round-trip via dns_pton()/dns_ntop().
 *   5. dns_strerror()     — error-code to string mapping.
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "udns.h"

static int failures = 0;
#define NCHECKS 11

#define CHECK(cond) do { \
    if (cond) { \
        printf("  [ok] %s\n", #cond); \
    } else { \
        printf("  [FAIL] %s\n", #cond); \
        ++failures; \
    } \
} while (0)

int main(void) {
    const char *ver;

    printf("test_udns: linking against udns %s\n", dns_version());

    /* 1. library initialization (offline-safe, do_open=0) */
    int ir = dns_init(NULL, 0);
    printf("dns_init(NULL,0) returned %d\n", ir);
    CHECK(ir == 0);

    /* 2. version string */
    ver = dns_version();
    printf("dns_version() = %s\n", ver ? ver : "(null)");
    CHECK(ver != NULL && ver[0] != '\0');

    /* 3. DN wire format round-trip */
    {
        unsigned char dn[256];
        char name[256];
        unsigned len = dns_sptodn("www.example.com", dn, sizeof(dn));
        printf("dns_sptodn length = %u\n", len);
        CHECK(len > 0);
        CHECK(dns_dnlen(dn) == len);
        CHECK(dns_dnlabels(dn) == 3);
        if (dns_dntosp(dn) != NULL) {
            printf("dns_dntosp = %s\n", dns_dntosp(dn));
            CHECK(strcmp(dns_dntosp(dn), "www.example.com") == 0);
        } else {
            CHECK(0); /* dns_dntosp returned NULL */
        }
        /* case-insensitive equality */
        {
            unsigned char dn2[256];
            dns_sptodn("WWW.Example.COM", dn2, sizeof(dn2));
            CHECK(dns_dnequal(dn, dn2) == len);
            (void)dns_dntop(dn, name, sizeof(name));
            printf("dns_dntop = %s\n", name);
            CHECK(strcmp(name, "www.example.com") == 0);
        }
    }

    /* 4. IP address round-trip */
    {
        char dst[64];
        struct in_addr a;
        int p = dns_pton(AF_INET, "192.168.1.1", &a);
        printf("dns_pton = %d\n", p);
        CHECK(p > 0);
        if (dns_ntop(AF_INET, &a, dst, sizeof(dst)) != NULL) {
            printf("dns_ntop = %s\n", dst);
            CHECK(strcmp(dst, "192.168.1.1") == 0);
        } else {
            CHECK(0); /* dns_ntop returned NULL */
        }
    }

    /* 5. error string */
    {
        const char *s = dns_strerror(DNS_E_NXDOMAIN);
        printf("dns_strerror(DNS_E_NXDOMAIN) = %s\n", s ? s : "(null)");
        CHECK(s != NULL && s[0] != '\0');
    }

    /* hmbs hard-gate marker — counts sourced from the same NCHECKS /
     * failures counters used in the RESULT lines above. */
    {
        int discovered = NCHECKS;
        int passed = NCHECKS - failures;
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_udns\",\"discovered\":%d,\"passedCount\":%d}\n",
               (failures == 0) ? "true" : "false", discovered, passed);
    }

    if (failures == 0) {
        printf("test_udns: RESULT %d/%d checks passed (udns %s)\n",
               NCHECKS, NCHECKS, ver ? ver : "");
        return 0;
    }
    fprintf(stderr, "test_udns: RESULT %d/%d checks passed, %d FAILED (udns %s)\n",
            NCHECKS - failures, NCHECKS, failures, ver ? ver : "");
    return 1;
}
