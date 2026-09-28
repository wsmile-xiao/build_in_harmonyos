/* Consumer smoke test for the packaged libmicrodns 0.2.0.
 *
 * Compiles against the installed public headers (microdns/microdns.h,
 * microdns/rr.h) and links the packaged library. Network-free and
 * deterministic: it validates error-string conversion (mdns_strerror),
 * public protocol constants, and rr_entry chain handling with
 * mdns_entries_print.
 */
#include <microdns/microdns.h>
#include <microdns/rr.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    printf("%s - %s\n", cond ? "ok" : "FAIL", what);
    if (!cond)
        failures++;
}

int main(void)
{
    char buf[256];

    /* 1-3: mdns_strerror only recognises the negative libmicrodns error
     * codes (MDNS_STDERR == -1 etc.); anything else falls through to the
     * default branch which reports failure and leaves the buffer empty. */
    memset(buf, 'x', sizeof(buf));
    check(mdns_strerror(0, buf, sizeof(buf)) == -1 && buf[0] == '\0',
          "mdns_strerror(0) reports unknown code and keeps the buffer empty");

    memset(buf, 0, sizeof(buf));
    check(mdns_strerror(-1, buf, sizeof(buf)) == 0 && buf[0] != '\0',
          "mdns_strerror(-1) yields a non-empty system error message");

    memset(buf, 'x', sizeof(buf));
    check(mdns_strerror(-1, buf, 0) == -1,
          "mdns_strerror with zero-size buffer is rejected");

    /* 4-6: public protocol constants. */
    check(MDNS_PORT == 5353, "MDNS_PORT is 5353");
    check(strcmp(MDNS_ADDR_IPV4, "224.0.0.251") == 0, "MDNS_ADDR_IPV4 is 224.0.0.251");
    check(strcmp(MDNS_ADDR_IPV6, "FF02::FB") == 0, "MDNS_ADDR_IPV6 is FF02::FB");

    /* 7: record type constants keep their RFC 1035/6762 values. */
    check(RR_A == 0x01 && RR_PTR == 0x0C && RR_TXT == 0x10 && RR_AAAA == 0x1C && RR_SRV == 0x21,
          "rr_type enum keeps its RFC values");

    /* 8: build a small PTR + A answer chain and print it through the
     * library; must traverse the chain without crashing. */
    {
        struct rr_entry ptr_entry, a_entry;
        struct rr_data_ptr ptr_data;
        struct rr_data_a a_data;
        const char *domain = "ohostest._harmonyos._tcp.local";

        memset(&ptr_entry, 0, sizeof(ptr_entry));
        memset(&a_entry, 0, sizeof(a_entry));
        memset(&ptr_data, 0, sizeof(ptr_data));
        memset(&a_data, 0, sizeof(a_data));

        ptr_data.domain = (char *)domain;
        ptr_entry.name = (char *)domain;
        ptr_entry.type = RR_PTR;
        ptr_entry.rr_class = RR_IN;
        ptr_entry.ttl = 120;
        ptr_entry.data.PTR = ptr_data;

        strcpy(a_data.addr_str, "192.168.1.10");
        a_entry.name = (char *)"ohostest.local";
        a_entry.type = RR_A;
        a_entry.rr_class = RR_IN;
        a_entry.ttl = 120;
        a_entry.data.A = a_data;

        ptr_entry.next = &a_entry;
        mdns_entries_print(&ptr_entry);
        ptr_entry.next = NULL;
        check(1, "mdns_entries_print walks a PTR+A chain without crashing");
    }

    if (failures != 0) {
        printf("%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("all 8 checks passed\n");
    return 0;
}
