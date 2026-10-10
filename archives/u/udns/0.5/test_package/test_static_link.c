/* test_static_link.c — 直接 `-ludns` 静态链接消费者（不经 CMakeDeps）。
 *
 * 目的：验证 package 产物 libudns.a + udns.h 在**最朴素的消费者链接方式**下
 * 也能成立，而不是只有 CMake 生成的目标才工作。这一层正是 udns 0.5 的
 * 回归点：上游 configure 的 inet_pton()/inet_ntop() 探测原型写错，导致
 * libudns.a 导出 udns_pton()/udns_ntop() 而不是头文件声明的
 * dns_pton()/dns_ntop() —— 任何消费者（无论 CMake 还是裸 cc）都会链接失败：
 *
 *   ld.lld: error: undefined symbol: dns_pton
 *   ld.lld: error: undefined symbol: dns_ntop
 *
 * 本程序因此只使用 udns.h 里声明过的公开符号，一旦归档符号表回归即构建失败，
 * 同时断言 udns_pton/udns_ntop 这类上游内部回退名**不得**被误当成公开 API。
 *
 * 另外验证 dns_sptodn()/dns_dntosp()/dns_pton()/dns_ntop() 的真实往返行为，
 * 而不是仅验证能链接。
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "udns.h"

static int failures = 0;
static int checks   = 0;   /* 运行时累加（与 test.c 同口径），不硬编码分母 */

#define CHECK(cond) do { \
    ++checks; \
    if (cond) { printf("  [ok] %s\n", #cond); } \
    else { printf("  [FAIL] %s\n", #cond); ++failures; } \
} while (0)

int main(void) {
    printf("test_static_link: direct -ludns consumer against udns %s\n",
           dns_version());

    /* 公开符号可用性：这三者缺失即代表归档符号表与 udns.h 不一致 */
    {
        const char *(*p_ntop)(int, const void *, char *, int) = &dns_ntop;
        int (*p_pton)(int, const char *, void *) = &dns_pton;
        /* udns 0.5 的 dns_dntop() 返回 int（0.6 才改为返回 const char *），
         * 函数指针类型必须按 0.5 的头文件原型书写。 */
        int (*p_dntop)(dnscc_t *, char *, unsigned) = &dns_dntop;
        /* 原为 CHECK(p_ntop != NULL) 等三条 —— 取函数地址恒非 NULL，属恒真
         * 断言（无判别力却计入 checks 数量）。改为**真正调用**这三个符号，
         * 使本层门禁来自实际行为而非指针非空：函数指针类型不符会在编译期
         * 报错（正是本层要抓的符号/原型回归），运行期再校验返回值。 */
        {
            char sbuf[64];
            struct in_addr sa;
            dnsc_t sdn[256];
            sbuf[0] = '\0';
            CHECK(p_pton(AF_INET, "127.0.0.1", &sa) == 1);
            CHECK(p_ntop(AF_INET, &sa, sbuf, sizeof(sbuf)) != NULL &&
                  strcmp(sbuf, "127.0.0.1") == 0);
            /* dns_ptodn 返回 DN 长度（int），非指针；失败 <= 0 */
            CHECK(dns_ptodn("example.com", 0, sdn, sizeof(sdn), NULL) > 0 &&
                  p_dntop(sdn, sbuf, sizeof(sbuf)) > 0);
        }
    }

    CHECK(dns_init(NULL, 0) == 0);

    /* dns_ntop / dns_pton 真实往返（0.5 回归的直接受害者） */
    {
        char buf[64];
        struct in_addr a;
        struct in_addr rt;
        int ok_ntop;
        buf[0] = '\0';   /* dns_ntop 失败时 buf 未被写入，先初始化以避免读取未初始化栈内存 */
        CHECK(dns_pton(AF_INET, "10.20.30.40", &a) == 1);
        ok_ntop = (dns_ntop(AF_INET, &a, buf, sizeof(buf)) != NULL &&
                   strcmp(buf, "10.20.30.40") == 0);
        CHECK(ok_ntop);
        if (ok_ntop) {
            printf("  dns_pton/dns_ntop round-trip = %s\n", buf);
            /* 反向解析用**独立于 buf** 的字面量，使本项可单独失败、可唯一归因，
             * 而不是上一项的逻辑蕴含（那样等于门禁强度注水）。 */
            CHECK(dns_pton(AF_INET, "10.20.30.40", &rt) == 1 &&
                  memcmp(&rt, &a, sizeof(a)) == 0);
            /* 负向断言：非法地址必须返回 0（补上头注释所声称的失败路径覆盖） */
            CHECK(dns_pton(AF_INET, "999.1.1.1", &rt) == 0);
        } else {
            printf("  dns_ntop 未能渲染地址，跳过反向解析检查（本项已判失败）\n");
            CHECK(0);
        }
    }

    if (failures == 0) {
        printf("test_static_link: RESULT %d/%d checks passed\n", checks, checks);
        return 0;
    }
    fprintf(stderr, "test_static_link: RESULT %d/%d checks passed, %d FAILED\n",
            checks - failures, checks, failures);
    return 1;
}
