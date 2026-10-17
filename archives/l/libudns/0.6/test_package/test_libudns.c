/*
 * test_libudns.c — Conan consumer test for libudns 0.6
 * 离线确定性测试: 真实调用 libudns 公开 API (无网络依赖),
 * 验证包内头文件与静态库可链接、API 语义正确。
 */
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include "udns.h"

#define CHECK(cond, msg) \
    do { if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return __LINE__; } } while (0)

int main(void)
{
    struct in_addr a4;
    char buf[INET_ADDRSTRLEN];
    char domain[DNS_MAXDN];
    int isabs = 0;
    int len;

    /* 1. dns_pton / dns_ntop 地址转换往返 */
    CHECK(dns_pton(AF_INET, "203.0.113.7", &a4) > 0, "dns_pton IPv4");
    CHECK(dns_ntop(AF_INET, &a4, buf, sizeof(buf)) != NULL,
          "dns_ntop IPv4");
    CHECK(strcmp(buf, "203.0.113.7") == 0, "IPv4 roundtrip");

    /* 2. 域名编码解码 */
    len = dns_ptodn("example.com.", 0, (unsigned char *)domain,
                    sizeof(domain), &isabs);
    CHECK(len > 0, "dns_ptodn positive length");
    CHECK(isabs != 0, "dns_ptodn absolute name");

    /* 3. 类型/类/状态名称表 */
    CHECK(strcmp(dns_typename(DNS_T_A), "A") == 0, "dns_typename A");
    CHECK(strcmp(dns_classname(DNS_C_IN), "IN") == 0, "dns_classname IN");
    CHECK(dns_strerror(0) != NULL, "dns_strerror non-null");

    /* 4. 解析器上下文可初始化 */
    if (dns_init(NULL, 0) < 0) {
        fprintf(stderr, "FAIL: dns_init\n");
        return __LINE__;
    }

    printf("libudns consumer test PASSED (version %s)\n", dns_version());
    return 0;
}