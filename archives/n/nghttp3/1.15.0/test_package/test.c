#include <stdio.h>
#include <stdlib.h>
#include <nghttp3/nghttp3.h>
#include <nghttp3/version.h>

int main(void) {
    const nghttp3_info *info = nghttp3_version(0);
    if (info == NULL) {
        fprintf(stderr, "nghttp3_version returned NULL\n");
        return 1;
    }
    printf("nghttp3 version: %s\n", info->version_str);
    printf("nghttp3 version_num: 0x%x\n", info->version_num);

    if (info->version_num != NGHTTP3_VERSION_NUM) {
        fprintf(stderr, "version mismatch: runtime=0x%x, header=0x%x\n",
                info->version_num, NGHTTP3_VERSION_NUM);
        return 1;
    }

    nghttp3_settings settings;
    nghttp3_settings_default(&settings);
    printf("nghttp3_settings_default: qpack_blocked_streams=%lu\n",
           (unsigned long)settings.qpack_blocked_streams);

    printf("test nghttp3 1.15.0: OK\n");
    return 0;
}
