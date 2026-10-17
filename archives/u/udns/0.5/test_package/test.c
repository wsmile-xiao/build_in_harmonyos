/* test_udns.c — Conan test_package consumer test for libudns (udns 0.5).
 *
 * Substantive verification (R34) in two layers:
 *
 *  A. Offline-deterministic API assertions (counted at runtime in `checks`):
 *     1. dns_init(NULL, 0)  — initialize resolver context (do_open=0: no
 *        network socket opened, safe in sandboxed/offline environments).
 *     2. dns_version()      — library version string matches the packaged
 *        version ("0.5"), so a silently-wrong source tarball is caught.
 *     3. Domain-name (DN) wire round-trip: dns_sptodn() -> dns_dntosp(),
 *        with dns_dnlen()/dns_dnlabels() proving label parsing works.
 *     4. dns_dnequal()      — case-insensitive DN equality.
 *     5. dns_dntop()        — ASCII presentation output.
 *     6. dns_pton()/dns_ntop() — IPv4 address conversion round-trip.
 *     7. dns_strerror()     — error-code to string mapping.
 *
 *  B. Real end-to-end asynchronous DNS resolution (rule 12 "鸿蒙特有测试"):
 *     dns_open() -> dns_submit_a4() -> poll(dns_sock) + dns_timeouts() +
 *     dns_ioevent() event loop -> dns_ntop() renders the answer. This drives
 *     the library's whole async resolver state machine (socket setup, query
 *     encoding, response parsing, RR decoding) exactly as a real consumer
 *     does, not merely isolated pure functions.
 *
 *     The sandbox/CI network may legitimately have no DNS reachability. In
 *     that case the check reports SKIP with the concrete errno/status text
 *     instead of pretending to pass — the reported pass count stays honest.
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/poll.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <errno.h>
#include <unistd.h>
#include "udns.h"

static int failures = 0;
static int checks  = 0;   /* 运行时累加的实际断言数（分母来自实测，不是硬编码） */
static int e2e_failed = 0; /* e2e 层独立结果，不并入离线断言分母 */

#define CHECK(cond) do { \
    ++checks; \
    if (cond) { \
        printf("  [ok] %s\n", #cond); \
    } else { \
        printf("  [FAIL] %s\n", #cond); \
        ++failures; \
    } \
} while (0)

/* ------------------------------------------------------------------ */
/* Part B: end-to-end async resolver round-trip                        */
/* ------------------------------------------------------------------ */

static int e2e_done;
static int e2e_ok;
static int e2e_nrr;
static int e2e_err;    /* 解析器明确回了错误（TEMPFAIL/SERVFAIL/NXDOMAIN 等）*/
static char e2e_first[64];

static void a4_cb(struct dns_ctx *ctx, struct dns_rr_a4 *result, void *data) {
    (void)data;
    if (!result) {
        /* 无应答（result == NULL）时的三态归因：
         *   · TEMPFAIL / NXDOMAIN / NODATA → **环境侧**，计 skipped（不计 e2e_err）：
         *     TEMPFAIL 是解析器瞬态故障；NXDOMAIN/NODATA 在默认 host(localhost)
         *     上是解析器的正常结果 —— 大量解析器对 localhost 直接返回 NXDOMAIN
         *     （libudns 不读 /etc/hosts）。若把它们当硬失败会造成离线环境**假红**，
         *     与 notes.md 的 skipped 承诺不符。
         *   · 其余（协议/格式类错误）→ 计 e2e_err，上报 failed。
         * 注意：本分支只在**根本没收到应答**时进入；"收到应答但值不对"由
         * e2e_nrr/e2e_ok 处理，判 failed（见函数末尾），不会被降级成 skipped。 */
        {
            int st = dns_status(ctx);
            if (st == DNS_E_TEMPFAIL || st == DNS_E_NXDOMAIN || st == DNS_E_NODATA) {
                printf("  [e2e] resolver returned %s (environmental, treated as skip)\n",
                       dns_strerror(st));
            } else {
                printf("  [e2e] A query failed: %s\n", dns_strerror(st));
                e2e_err = 1;
            }
        }
        e2e_done = 1;
        return;
    }
    e2e_nrr = result->dnsa4_nrr;
    if (e2e_nrr > 0) {
        int i;
        for (i = 0; i < e2e_nrr; i++) {
            char buf[INET_ADDRSTRLEN];
            /* 显式 != NULL，与本文件另一处口径统一；并要求确实写入内容，
             * 避免返回非 NULL 却未写入时把空串当成成功渲染。 */
            if (dns_ntop(AF_INET, &result->dnsa4_addr[i], buf, sizeof(buf)) != NULL
                && buf[0] != '\0') {
                if (!e2e_first[0]) {
                    snprintf(e2e_first, sizeof(e2e_first), "%s", buf);
                    /* 只有**真的渲染出地址**才算 e2e 成功。
                     * 原来 e2e_ok 仅由 nrr>0 决定，若 dns_ntop 全部失败仍会输出
                     * status:"passed" 且 first:"" —— 与 test_udns_ohos.c 要求
                     * strcmp(first,"127.0.0.1")==0 的标准不一致。 */
                    e2e_ok = 1;
                }
                printf("  [e2e] A record %d: %s\n", i, buf);
            }
        }
    }
    e2e_done = 1;
}

/* 三态契约：1 = 解析成功且渲染出地址；-1 = 收到应答但异常/解析器明确回错；
 *           0 = 环境不可达或配置失败（skipped） */
static int e2e_resolve(const char *host, int timeout_sec) {
    time_t start;
    int opened;

    /* 重置共享状态（与 test_udns_ohos.c::resolve_via 一致）：否则二次调用会
     * 沿用上一轮结果造成"假通过"。 */
    e2e_done = e2e_ok = e2e_nrr = e2e_err = 0;
    e2e_first[0] = '\0';

    if (dns_init(NULL, 0) < 0) {
        /* 环境/配置失败 → 0(skipped)，与 test_udns_ohos.c::resolve_via 同口径。
         * -1 只保留给"收到应答但结果异常"。原实现返回 -1，会让离线/沙箱环境
         * 因 dns_init 失败而整体假红，与 main() 注释 "may SKIP when offline"
         * 及 E2E_DNS_RESULT 的 skipped 分支自相矛盾。 */
        printf("  [e2e] dns_init failed\n");
        dns_close(NULL);   /* 与其它出口成对释放，避免半初始化上下文残留 */
        return 0;
    }
    opened = dns_open(NULL);
    if (opened < 0) {
        printf("  [e2e] dns_open unavailable: %s (errno=%d %s)\n",
               dns_strerror(dns_status(NULL)), errno, strerror(errno));
        dns_close(NULL);
        return 0;   /* no local /etc/resolv.conf -> offline environment */
    }
    if (!dns_submit_a4(NULL, host, 0, a4_cb, NULL)) {
        /* 同属环境/配置类失败 → skipped */
        printf("  [e2e] dns_submit_a4 failed: %s\n", dns_strerror(dns_status(NULL)));
        dns_close(NULL);
        return 0;
    }
    start = time(NULL);
    while (!e2e_done) {
        struct pollfd pfd;
        time_t now = time(NULL);
        int c, to;
        pfd.fd = dns_sock(NULL);
        pfd.events = POLLIN;
        pfd.revents = 0;                  /* 必须清零，否则复用上一轮的状态 */
        to = dns_timeouts(NULL, -1, now);
        if (to < 0) to = 1;
        /* 与 test_udns_ohos.c 同口径：夹紧到**剩余预算**，避免 to*1000
         * 有符号溢出，也避免总等待被拉长到 ~2x timeout_sec。 */
        /* 仅在**预算耗尽**时退出；to==0（定时器到期/无待办）不能提前 break，
         * 否则已到达的报文会被漏读，真失败被降级成 skipped（假绿）。 */
        if ((int)(now - start) >= timeout_sec)
            break;
        if (to > timeout_sec - (int)(now - start))
            to = timeout_sec - (int)(now - start);
        /* to==0（定时器已到期）时若 poll 0ms 会空转，而 time() 是秒级粒度，
         * 最坏白烧约 1s CPU。给 10ms 下限，让出 CPU 又不影响判定。 */
        if (to < 1)
            to = 1;
        c = poll(&pfd, 1, to * 1000 > 10 ? to * 1000 : 10);
        now = time(NULL);
        if (c > 0) {
            /* c>0 不代表可读：POLLERR/POLLHUP/POLLNVAL 也会返回 >0。
             * 原实现无条件调 dns_ioevent()，socket 出错时会形成忙等紧循环。 */
            if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) {
                printf("  [e2e] socket error (revents=0x%x)\n", pfd.revents);
                dns_close(NULL);   /* 与本函数其它出口成对释放 */
                return -1;
            }
            if (pfd.revents & POLLIN)
                dns_ioevent(NULL, now);
        }
        if (now - start > timeout_sec)
            break;
    }
    dns_close(NULL);

    /* 统一三态契约（与 test_udns_ohos.c 一致）：
     *   1 = 解析成功且渲染出地址
     *  -1 = 收到应答但异常 / 解析器明确回了错误（真实失败，必须判 failed）
     *   0 = 环境不可达（无应答且非明确错误）→ skipped
     * 原实现只要 !e2e_ok 就 return 0，导致"收到应答但解码/渲染失败"以及协议类
     * 错误永远无法让 e2e 层失败（假绿）。 */
    if (e2e_ok)
        return 1;
    /* 收到应答（e2e_nrr>0）却始终未能渲染出地址：这是**解码链路缺陷**，
     * 必须判 -1(failed)，不能落入 skipped —— 否则真实的地址渲染失败会被
     * 伪装成"环境不可达"（与 test_udns_ohos.c 的 cb_got_answer 口径一致）。 */
    if (e2e_err || e2e_nrr > 0)
        return -1;
    printf("  [e2e] no A record (status=%s, elapsed=%lds)\n",
           dns_strerror(dns_status(NULL)), (long)(time(NULL) - start));
    return 0;
}

int main(void) {
    const char *ver;

    ver = dns_version();
    printf("test_udns: linking against udns %s\n", ver ? ver : "(null)");

    /* 1. library initialization (offline-safe, do_open=0) */
    {
        int ir = dns_init(NULL, 0);
        printf("dns_init(NULL,0) returned %d\n", ir);
        CHECK(ir == 0);
    }

    /* 2. version string must be the packaged version */
    printf("dns_version() = %s\n", ver ? ver : "(null)");
    CHECK(ver != NULL && ver[0] != '\0');
    CHECK(ver != NULL && strcmp(ver, "0.5") == 0);

    /* 3. DN wire format round-trip */
    {
        unsigned char dn[256];
        char name[256];
        int len;
        /* 与下方 name 同样的防护：udns 失败时根本不写输出缓冲，
         * 直接读 dn 是未初始化栈内存、判定不确定。先清零，并把依赖
         * "已成功转换"的三个解析断言收进 if (len > 0)。 */
        memset(dn, 0, sizeof(dn));
        len = dns_sptodn("www.example.com", dn, sizeof(dn));
        printf("dns_sptodn length = %d\n", len);
        CHECK(len > 0);
        if (len > 0) {
            CHECK(dns_dnlen(dn) == len);
            CHECK(dns_dnlabels(dn) == 3);
            if (dns_dntosp(dn) != NULL) {
                printf("dns_dntosp = %s\n", dns_dntosp(dn));
                CHECK(strcmp(dns_dntosp(dn), "www.example.com") == 0);
            } else {
                CHECK(0);
            }
        } else {
            printf("  dns_sptodn 失败，跳过依赖其输出的解析检查（本项已判失败）\n");
            CHECK(0);
        }
        {
            unsigned char dn2[256];
            dns_sptodn("WWW.Example.COM", dn2, sizeof(dn2));
            CHECK(dns_dnequal(dn, dn2) == len);
            /* udns 失败时**根本不写 name**，直接 printf/strcmp 会读未初始化
             * 栈内存、判定不确定。预置空串并捕获返回值，仅 >0 时比较。 */
            int dnrc;
            name[0] = '\0';
            dnrc = dns_dntop(dn, name, sizeof(name));
            printf("dns_dntop = %s\n", name);
            CHECK(dnrc > 0 && strcmp(name, "www.example.com") == 0);
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
            CHECK(0);
        }
    }

    /* 5. error string */
    {
        const char *s = dns_strerror(DNS_E_NXDOMAIN);
        printf("dns_strerror(DNS_E_NXDOMAIN) = %s\n", s ? s : "(null)");
        CHECK(s != NULL && s[0] != '\0');
    }

    /* 6. end-to-end async resolution round-trip (may SKIP when offline) */
    {
        const char *host = getenv("UDNS_TEST_HOST");
        int rc;
        if (!host || !host[0])
            host = "localhost";
        /* host 来自环境变量并会被插进 JSON 标记（CI 的证据通道）。含引号/反斜杠
         * 会产出非法 JSON 甚至伪造 status；非白名单字符一律退回默认值。 */
        {
            const char *q;
            for (q = host; *q; q++) {
                if (!(isalnum((unsigned char)*q) || *q == '.' || *q == '-' || *q == '_')) {
                    printf("  [e2e] UDNS_TEST_HOST contains unsafe chars; using default\n");
                    host = "localhost";
                    break;
                }
            }
        }
        printf("e2e: async dns_submit_a4(\"%s\") -> poll/dns_ioevent -> dns_ntop\n", host);
        rc = e2e_resolve(host, 15);
        if (rc == 1) {
            printf("E2E_DNS_RESULT={\"status\":\"passed\",\"host\":\"%s\","
                   "\"nrr\":%d,\"first\":\"%s\"}\n", host, e2e_nrr, e2e_first);
        } else if (rc == 0) {
            printf("E2E_DNS_RESULT={\"status\":\"skipped\",\"host\":\"%s\","
                   "\"reason\":\"no DNS reachability in this environment "
                   "(dns_open/nxdomain/no answer); offline deterministic "
                   "assertions still enforced\"}\n", host);
        } else {
            printf("E2E_DNS_RESULT={\"status\":\"failed\",\"host\":\"%s\"}\n", host);
            /* e2e 是**独立于**离线确定性断言的一层：它有自己的分母。
             * 绝不能 ++failures —— 那样会把 e2e 的失败从离线断言分母里扣掉，
             * 输出 "11/12" 让人误以为某条离线断言挂了（实测离线是 12/12），
             * 导致 CI 的失败归因指向错误的层。 */
            e2e_failed = 1;
        }
    }

    /* hmbs hard-gate marker — 分母/分子都取自**运行时累加**的 checks，
     * 不再硬编码，避免断言增删后门禁数字静默失真。e2e 层单列，不混入本分母。 */
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"test_udns\",\"discovered\":%d,\"passedCount\":%d,"
           "\"e2e_failed\":%d}\n",
           (failures == 0 && e2e_failed == 0) ? "true" : "false",
           checks, checks - failures, e2e_failed);

    if (failures == 0 && e2e_failed == 0) {
        printf("test_udns: RESULT %d/%d checks passed (udns %s)\n",
               checks, checks, ver ? ver : "");
        return 0;
    }
    fprintf(stderr, "test_udns: RESULT %d/%d offline checks passed, %d FAILED%s (udns %s)\n",
            checks - failures, checks, failures,
            e2e_failed ? " + e2e layer failed" : "", ver ? ver : "");
    return 1;
}
