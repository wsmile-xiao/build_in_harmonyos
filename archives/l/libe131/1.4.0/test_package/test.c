#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <e131.h>

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    printf("[run] %s\n", #fn); \
    tests_run++; \
    if ((fn)() != 0) { \
        tests_failed++; \
        printf("  [FAIL] %s\n", #fn); \
    } else { \
        printf("  [ok] %s\n", #fn); \
    } \
} while (0)

static int test_pkt_init(void) {
    e131_packet_t packet;
    if (e131_pkt_init(&packet, 1, 24) != 0)
        return 1;
    if (ntohs(packet.root.preamble_size) != 0x0010)
        return 2;
    if (ntohs(packet.root.postamble_size) != 0x0000)
        return 3;
    if (packet.frame.priority != E131_DEFAULT_PRIORITY)
        return 4;
    if (ntohs(packet.frame.universe) != 1)
        return 5;
    if (ntohs(packet.dmp.prop_val_cnt) != 25)
        return 6;
    if (sizeof(packet.raw) != 638)
        return 7;
    if (e131_pkt_init(&packet, 63999, 512) != 0)
        return 8;
    if (ntohs(packet.dmp.prop_val_cnt) != 513)
        return 9;
    return 0;
}

static int test_pkt_init_reject(void) {
    e131_packet_t packet;
    if (e131_pkt_init(NULL, 1, 24) == 0)
        return 1;
    if (e131_pkt_init(&packet, 0, 24) == 0)
        return 2;
    if (e131_pkt_init(&packet, 64000, 24) == 0)
        return 3;
    if (e131_pkt_init(&packet, 1, 0) == 0)
        return 4;
    if (e131_pkt_init(&packet, 1, 513) == 0)
        return 5;
    return 0;
}

static int test_options(void) {
    e131_packet_t packet;
    if (e131_pkt_init(&packet, 7, 8) != 0)
        return 1;
    if (e131_get_option(&packet, E131_OPT_PREVIEW))
        return 2;
    if (e131_set_option(&packet, E131_OPT_PREVIEW, true) != 0)
        return 3;
    if (!e131_get_option(&packet, E131_OPT_PREVIEW))
        return 4;
    if (e131_set_option(&packet, E131_OPT_PREVIEW, false) != 0)
        return 5;
    if (e131_get_option(&packet, E131_OPT_PREVIEW))
        return 6;
    if (e131_set_option(&packet, E131_OPT_TERMINATED, true) != 0)
        return 7;
    if (!e131_get_option(&packet, E131_OPT_TERMINATED))
        return 8;
    if (e131_set_option(NULL, E131_OPT_PREVIEW, true) == 0)
        return 9;
    return 0;
}

static int test_validate(void) {
    e131_packet_t packet;
    if (e131_pkt_init(&packet, 3, 16) != 0)
        return 1;
    if (e131_pkt_validate(&packet) != E131_ERR_NONE)
        return 2;
    if (e131_pkt_validate(NULL) != E131_ERR_NULLPTR)
        return 3;
    packet.root.preamble_size = 0;
    if (e131_pkt_validate(&packet) != E131_ERR_PREAMBLE_SIZE)
        return 4;
    if (e131_pkt_init(&packet, 3, 16) != 0)
        return 5;
    packet.root.acn_pid[0] ^= 0xff;
    if (e131_pkt_validate(&packet) != E131_ERR_ACN_PID)
        return 6;
    if (e131_pkt_init(&packet, 3, 16) != 0)
        return 7;
    packet.dmp.type ^= 0xff;
    if (e131_pkt_validate(&packet) != E131_ERR_TYPE_DMP)
        return 8;
    return 0;
}

static int test_dest(void) {
    e131_addr_t dest;
    char str[22];
    if (e131_multicast_dest(&dest, 1, E131_DEFAULT_PORT) != 0)
        return 1;
    if (dest.sin_family != AF_INET)
        return 2;
    if (ntohs(dest.sin_port) != E131_DEFAULT_PORT)
        return 3;
    if (strcmp(inet_ntoa(dest.sin_addr), "239.255.0.1") != 0)
        return 4;
    if (e131_multicast_dest(&dest, 44000, E131_DEFAULT_PORT) != 0)
        return 5;
    if (strcmp(inet_ntoa(dest.sin_addr), "239.255.171.224") != 0)
        return 6;
    if (e131_multicast_dest(NULL, 1, E131_DEFAULT_PORT) == 0)
        return 7;
    if (e131_multicast_dest(&dest, 0, E131_DEFAULT_PORT) == 0)
        return 8;
    if (e131_multicast_dest(&dest, 64000, E131_DEFAULT_PORT) == 0)
        return 9;
    if (e131_unicast_dest(&dest, "127.0.0.1", E131_DEFAULT_PORT) != 0)
        return 10;
    if (strcmp(inet_ntoa(dest.sin_addr), "127.0.0.1") != 0)
        return 11;
    if (e131_dest_str(str, &dest) != 0)
        return 12;
    if (strcmp(str, "127.0.0.1:5568") != 0)
        return 13;
    if (e131_dest_str(NULL, &dest) == 0)
        return 14;
    if (E131_DEFAULT_PORT != 5568)
        return 15;
    if (E131_DEFAULT_PRIORITY != 100)
        return 16;
    return 0;
}

static int test_discard_strerror_dump(void) {
    e131_packet_t packet;
    if (e131_pkt_init(&packet, 9, 4) != 0)
        return 1;
    packet.frame.seq_number = 10;
    if (e131_pkt_discard(&packet, 9))
        return 2;
    if (!e131_pkt_discard(&packet, 10))
        return 3;
    if (!e131_pkt_discard(&packet, 11))
        return 4;
    if (!e131_pkt_discard(NULL, 10))
        return 5;
    if (e131_strerror(E131_ERR_NONE) == NULL)
        return 6;
    if (e131_strerror(E131_ERR_PREAMBLE_SIZE) == NULL)
        return 7;
    if (e131_strerror(E131_ERR_ACN_PID) == NULL)
        return 8;
    if (e131_strerror(E131_ERR_VECTOR_DMP) == NULL)
        return 9;
    if (e131_pkt_dump(stdout, &packet) != 0)
        return 10;
    if (e131_pkt_dump(NULL, &packet) == 0)
        return 11;
    if (e131_pkt_dump(stdout, NULL) == 0)
        return 12;
    return 0;
}

int main(void) {
    printf("=== libe131 1.4.0 consumer tests (OpenHarmony/aarch64) ===\n");
    RUN(test_pkt_init);
    RUN(test_pkt_init_reject);
    RUN(test_options);
    RUN(test_validate);
    RUN(test_dest);
    RUN(test_discard_strerror_dump);
    printf("=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);
    {
        int discovered = 6;
        int executed = tests_run;
        int passed = tests_run - tests_failed;
        int failed = tests_failed;
        int skipped = 0;
        const char *status = (failed == 0) ? "passed" : "failed";
        printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"autotools\",\"command\":\"make check\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"libe131-1.4.0.tar.gz audited: no tests/ or test/ directory, no TEST/TEST_F/gtest, no def test_/pytest, Makefile.am defines no check/TESTS target, configure.ac has no test macros; examples/ holds only infinite-loop demos (test_client.c/test_server.c), not an automated suite\"}\n");
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_libe131\",\"discovered\":%d,\"passedCount\":%d}\n",
               (failed == 0) ? "true" : "false", discovered, passed);
        (void)status;
        (void)executed;
        (void)skipped;
    }
    return tests_failed == 0 ? 0 : 1;
}
