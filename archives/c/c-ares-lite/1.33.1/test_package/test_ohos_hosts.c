/* test_ohos_hosts.c — c-ares-lite 1.33.1 鸿蒙特有测试
 *
 * 真实调用 c-ares API 验证 OHOS hosts/HMDFS 平台路径的 localhost 解析行为：
 *   - ares_init_options / ares_gethostbyname("localhost", AF_INET)
 *   - ares_process 驱动回调，断言返回 127.0.0.1（/etc/hosts -> HMDFS hosts_user）
 * 该测试独立于通用 test_package 冒烟（test.c）与 L1e/W3 依赖门禁负测。
 */
#include <stdio.h>
#include <string.h>
#include <netdb.h>
#include <ares.h>

static void host_cb(void *arg, int status, int timeouts, struct hostent *host) {
    (void)timeouts;
    if (status != ARES_SUCCESS) {
        fprintf(stderr, "ares_gethostbyname failed: %s\n", ares_strerror(status));
        *(int *)arg = status;
        return;
    }
    if (!host || !host->h_addr_list || !host->h_addr_list[0]) {
        fprintf(stderr, "no address returned for localhost\n");
        *(int *)arg = -2;
        return;
    }
    unsigned char *a = (unsigned char *)host->h_addr_list[0];
    if (host->h_addrtype == AF_INET && a[0] == 127 && a[1] == 0 && a[2] == 0 && a[3] == 1) {
        printf("c-ares-lite OHOS hosts/HMDFS localhost -> 127.0.0.1 OK\n");
        *(int *)arg = 0;
    } else {
        fprintf(stderr, "unexpected localhost resolution (addrtype=%d)\n", host->h_addrtype);
        *(int *)arg = -3;
    }
}

int main(void) {
    ares_channel channel;
    struct ares_options opts;
    int done = -1;
    int status;

    memset(&opts, 0, sizeof(opts));
    status = ares_init_options(&channel, &opts, ARES_OPT_TIMEOUTMS | ARES_OPT_TRIES);
    if (status != ARES_SUCCESS) {
        fprintf(stderr, "ares_init_options failed: %s\n", ares_strerror(status));
        return 2;
    }

    ares_gethostbyname(channel, "localhost", AF_INET, host_cb, &done);
    ares_process(channel, NULL, NULL);
    ares_destroy(channel);

    if (done == 0) {
        printf("test c-ares-lite ohos hosts path: PASS\n");
        return 0;
    }
    fprintf(stderr, "test c-ares-lite ohos hosts path: FAIL (rc=%d)\n", done);
    return 1;
}
