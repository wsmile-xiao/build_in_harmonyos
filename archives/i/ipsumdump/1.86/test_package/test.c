#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Minimal valid pcap file embedded as byte array.
   Generated at runtime to avoid binary files in git/PR diff.
   Format: pcap global header (24 bytes) + packet header (16 bytes) + packet data.
   Packet: 14B Ethernet + 20B IP + 8B ICMP echo = 42 bytes total. */
static const unsigned char pcap_data[] = {
    /* Global header (24 bytes) */
    0xd4, 0xc3, 0xb2, 0xa1,  /* magic (microsecond) */
    0x02, 0x00,              /* version major 2 */
    0x04, 0x00,              /* version minor 4 */
    0x00, 0x00, 0x00, 0x00,  /* timezone */
    0x00, 0x00, 0x00, 0x00,  /* sigfigs */
    0xff, 0xff, 0x00, 0x00,  /* snaplen 65535 */
    0x01, 0x00, 0x00, 0x00,  /* network: Ethernet (1) */
    /* Packet header (16 bytes) */
    0x00, 0x00, 0x00, 0x00,  /* timestamp seconds */
    0x00, 0x00, 0x00, 0x00,  /* timestamp microseconds */
    0x2a, 0x00, 0x00, 0x00,  /* captured length 42 */
    0x2a, 0x00, 0x00, 0x00,  /* original length 42 */
    /* Ethernet header (14 bytes): dst MAC + src MAC + EtherType IPv4 */
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05,
    0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
    0x08, 0x00,
    /* IP header (20 bytes): v4/IHL 5, total len 40, TTL 64, proto ICMP */
    0x45, 0x00, 0x00, 0x28, 0x00, 0x00, 0x40, 0x00,
    0x40, 0x01, 0x00, 0x00, 0xc0, 0xa8, 0x00, 0x01,
    0xc0, 0xa8, 0x00, 0x02,
    /* ICMP echo (8 bytes): type 8, code 0 */
    0x08, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01
};
static const unsigned int pcap_len = sizeof(pcap_data);

static int write_pcap(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "[FAIL] cannot create %s\n", path);
        return -1;
    }
    if (fwrite(pcap_data, 1, pcap_len, f) != pcap_len) {
        fprintf(stderr, "[FAIL] short write to %s\n", path);
        fclose(f);
        return -1;
    }
    fclose(f);
    return 0;
}

int main(void) {
    int ret;
    const char *tmpdir;
    char pcap_path[512];

    /* Determine writable directory: use TMPDIR or HOME/tmp */
    tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = getenv("HOME");
    if (!tmpdir) tmpdir = "/data/local/tmp";
    snprintf(pcap_path, sizeof(pcap_path), "%s/test_ipsumdump.pcap", tmpdir);

    /* Write embedded pcap data to temporary file */
    if (write_pcap(pcap_path) != 0)
        return 1;

    /* Test 1: ipsumdump --version */
    printf("[test] checking ipsumdump --version ...\n");
    ret = system("ipsumdump --version > /dev/null 2>&1");
    if (ret != 0) {
        printf("[FAIL] ipsumdump --version returned %d\n", ret);
        return 1;
    }
    printf("[PASS] ipsumdump --version works\n");

    /* Test 2: ipsumdump -c -r on generated pcap file */
    printf("[test] checking ipsumdump -c -r %s ...\n", pcap_path);
    {
        char cmd[640];
        snprintf(cmd, sizeof(cmd), "ipsumdump -c -r %s > /dev/null 2>&1", pcap_path);
        ret = system(cmd);
    }
    if (ret != 0) {
        printf("[FAIL] ipsumdump -c -r returned %d\n", ret);
        return 1;
    }
    printf("[PASS] ipsumdump -c -r works\n");

    /* Cleanup */
    remove(pcap_path);

    printf("All test_package tests passed!\n");
    return 0;
}
