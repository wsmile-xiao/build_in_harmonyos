#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pcap.h>

/* HarmonyOS consumer test — validates pcap API on OHOS platform */

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name, expr) do { \
    tests_run++; \
    if (expr) { \
        tests_passed++; \
        printf("  [PASS] %s\n", name); \
    } else { \
        printf("  [FAIL] %s\n", name); \
    } \
} while(0)

int main(void) {
    printf("=== libpcap %s — HarmonyOS consumer tests ===\n\n", pcap_lib_version());

    /* 1. Version string */
    TEST("pcap_lib_version returns non-empty",
         pcap_lib_version() != NULL && strlen(pcap_lib_version()) > 0);

    /* 2. Open dead handle (DLT_EN10MB, 65535 snap) */
    pcap_t *dead = pcap_open_dead(DLT_EN10MB, 65535);
    TEST("pcap_open_dead(DLT_EN10MB) succeeds", dead != NULL);

    if (dead) {
        /* 3. Snapshot length */
        TEST("pcap_snapshot == 65535", pcap_snapshot(dead) == 65535);

        /* 4. BPF compile (simple expression) */
        struct bpf_program fp;
        int rc = pcap_compile(dead, &fp, "ip and tcp", 1, PCAP_NETMASK_UNKNOWN);
        TEST("pcap_compile('ip and tcp') succeeds", rc == 0);
        if (rc == 0) {
            TEST("compiled filter has >0 insns", fp.bf_len > 0);
            pcap_freecode(&fp);
        }

        /* 6. BPF compile (complex expression) */
        rc = pcap_compile(dead, &fp, "tcp port 80 or tcp port 443", 1, PCAP_NETMASK_UNKNOWN);
        TEST("pcap_compile('tcp port 80/443') succeeds", rc == 0);
        if (rc == 0) {
            pcap_freecode(&fp);
        }

        /* 7. Invalid BPF expression */
        rc = pcap_compile(dead, &fp, "invalid_filter_xyz", 1, PCAP_NETMASK_UNKNOWN);
        TEST("pcap_compile(invalid) returns error", rc != 0);

        /* 8. Datalink name/description mapping */
        const char *name = pcap_datalink_val_to_name(DLT_EN10MB);
        TEST("pcap_datalink_val_to_name(DLT_EN10MB) != NULL", name != NULL);
        TEST("name == 'EN10MB'", name != NULL && strcmp(name, "EN10MB") == 0);

        const char *desc = pcap_datalink_val_to_description(DLT_EN10MB);
        TEST("pcap_datalink_val_to_description(DLT_EN10MB) != NULL", desc != NULL);

        /* 9. Reverse mapping */
        int val = pcap_datalink_name_to_val("EN10MB");
        TEST("pcap_datalink_name_to_val('EN10MB') == DLT_EN10MB", val == DLT_EN10MB);

        pcap_close(dead);
    }

    printf("\n=== Results: %d/%d passed ===\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
