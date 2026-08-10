#include <stdio.h>
#include <ngtcp2/ngtcp2.h>

int main(void) {
    const ngtcp2_info *info = ngtcp2_version(0);
    if (info == NULL || info->version_str == NULL) {
        fprintf(stderr, "ngtcp2_version returned NULL\n");
        return 1;
    }
    printf("ngtcp2 version: %s\n", info->version_str);

    uint8_t dcid_data[] = {0x01, 0x02, 0x03, 0x04};
    uint8_t scid_data[] = {0x05, 0x06};

    uint8_t buf[256];
    uint32_t versions[] = {0x00000001};
    ngtcp2_ssize n = ngtcp2_pkt_write_version_negotiation(
        buf, sizeof(buf), 0x00,
        dcid_data, sizeof(dcid_data),
        scid_data, sizeof(scid_data),
        versions, 1);
    if (n <= 0) {
        fprintf(stderr, "ngtcp2_pkt_write_version_negotiation failed: %zd\n", n);
        return 1;
    }
    printf("Version negotiation packet written: %zd bytes\n", n);
    printf("All tests passed\n");
    return 0;
}
