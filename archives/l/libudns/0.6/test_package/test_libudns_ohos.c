/*
 * test_libudns_ohos.c — HarmonyOS 专项测试: 真实调用 libudns 异步 DNS API
 * 在 OHOS aarch64 平台验证 libudns 0.6 解析器可用性:
 *   dns_init -> dns_submit_a4 -> dns_ioevent 事件循环 -> dns_ntop 结果回显
 * 编译: clang -I<prefix>/include test_libudns_ohos.c -L<prefix>/lib -ludns -o test_libudns_ohos
 * 运行: ./test_libudns_ohos [hostname]  (默认 example.com)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/poll.h>
#include <arpa/inet.h>
#include "udns.h"

static int query_done = 0;
static int query_ok = 0;

static void a4_cb(struct dns_ctx *ctx, struct dns_rr_a4 *result, void *data)
{
    (void)data;
    if (!result) {
        fprintf(stderr, "A query failed: %s\n", dns_strerror(dns_status(ctx)));
        query_done = 1;
        return;
    }
    printf("A query OK, %d A record(s):\n", result->dnsa4_nrr);
    for (int i = 0; i < result->dnsa4_nrr; i++) {
        char buf[INET_ADDRSTRLEN];
        if (dns_ntop(AF_INET, &result->dnsa4_addr[i], buf, sizeof(buf)))
            printf("  %s\n", buf);
    }
    query_ok = result->dnsa4_nrr > 0;
    query_done = 1;
}

int main(int argc, char **argv)
{
    const char *host = argc > 1 ? argv[1] : "example.com";
    time_t start;

    printf("libudns %s HarmonyOS test: resolving %s ...\n",
           dns_version(), host);
    fflush(stdout);

        if (dns_init(NULL, 1) < 0) {
        fprintf(stderr, "dns_init failed\n");
        return 1;
    }
    if (!dns_submit_a4(NULL, host, 0, a4_cb, NULL)) {
        fprintf(stderr, "dns_submit_a4 failed: %s\n",
                dns_strerror(dns_status(NULL)));
        return 1;
    }
    start = time(NULL);
    while (!query_done) {
        struct pollfd pfd;
        time_t now = time(NULL);
        int c;
        pfd.fd = dns_sock(NULL);
        pfd.events = POLLIN;
        c = dns_timeouts(NULL, -1, now);
        c = poll(&pfd, 1, c < 0 ? 1000 : c * 1000);
        now = time(NULL);
        if (c > 0)
            dns_ioevent(NULL, now);
        if (now - start > 20) {
            fprintf(stderr, "TIMEOUT waiting for DNS answer\n");
            return 1;
        }
    }
    if (!query_ok) {
        fprintf(stderr, "no A record resolved\n");
        return 1;
    }
    printf("libudns HarmonyOS test PASSED\n");
    return 0;
}
