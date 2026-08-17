#include <stdio.h>
#include <ngtcp2/ngtcp2.h>

int main(void) {
    const ngtcp2_info *info = ngtcp2_version(0);
    if (info == NULL) {
        fprintf(stderr, "ngtcp2_version() returned NULL\n");
        return 1;
    }
    printf("ngtcp2 version: %s (num: %d)\n", info->version_str, info->version_num);
    return 0;
}
