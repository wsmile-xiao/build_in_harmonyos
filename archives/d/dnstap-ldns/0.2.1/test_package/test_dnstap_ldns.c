/*
 * test_dnstap_ldns.c — L0c 真实测试源（消费者验证，非空壳）。
 *
 * 通过已安装的 dnstap-ldns 二进制（bin/dnstap-ldns）的 -x/-x -y 公开 CLI
 * 路径解码一段真实 hex 编码的 dnstap protobuf 帧，并断言可观察输出：
 *   Dnstap{ type=MESSAGE,
 *           message={ type=AUTH_QUERY, socket_family=INET,
 *                     socket_protocol=UDP, query_address=127.0.0.1,
 *                     query_port=53, response_port=53 } }
 * hex: 7801721008011001180122047f00000130353835
 * 断言（3 项）：
 *   1) quiet 输出含 "AQ"（AUTH_QUERY 助记符）
 *   2) quiet 输出含 "127.0.0.1"（query_address 呈现形式）
 *   3) YAML(-y) 输出含 "AUTH_QUERY"（完整消息类型）
 * 任一断言失败 → 非 0 退出；全部通过 → 0 退出并打印验收行。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *HEX_INPUT =
    "7801721008011001180122047f00000130353835";

/* 运行 <bin> -x [extra] < HEX_INPUT，断言输出包含 expect。 */
static int run_decode(const char *bin, const char *extra, const char *expect)
{
    char cmd[1200];
    char buf[4096];
    size_t n;
    int rc;

    snprintf(cmd, sizeof(cmd), "printf '%s' | \"%s\" -x %s",
             HEX_INPUT, bin, extra ? extra : "");
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "[%s] popen failed\n", expect);
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = 0;
    rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "[%s] decode rc=%d output=%s\n", expect, rc, buf);
        return 1;
    }
    if (!strstr(buf, expect)) {
        fprintf(stderr, "[%s] missing in output: %s\n", expect, buf);
        return 1;
    }
    printf("OK: output contains %s\n", expect);
    return 0;
}

int main(int argc, char **argv)
{
    const char *bin;

    if (argc < 2) {
        fprintf(stderr, "usage: test_dnstap_ldns <path-to-bin/dnstap-ldns>\n");
        return 2;
    }
    bin = argv[1];

    if (run_decode(bin, "", "AQ") != 0)
        return 1;
    if (run_decode(bin, "", "127.0.0.1") != 0)
        return 1;
    if (run_decode(bin, "-y", "AUTH_QUERY") != 0)
        return 1;

    printf("test_dnstap_ldns: all decode assertions passed\n");
    return 0;
}