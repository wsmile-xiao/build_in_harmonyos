/*
 * dnswire HarmonyOS PC 专项测试
 *
 * 验证库在 HarmonyOS PC (aarch64, clang 15) 上的实际可用性：
 *   1. dnstap protobuf 编码往返：构造一条真实的 DNS 事件消息（query + response），
 *      用公开 API dnstap_encode_protobuf() 编码为 protobuf 字节流，再用
 *      dnstap_decode_protobuf() 解码，逐字段核对往返一致性。
 *   2. 动态库加载：通过链接 libdnswire 并解析符号，验证 soname/符号表在
 *      OHOS 动态加载器下可用（本测试同时以 .so 链接运行方式覆盖）。
 *   3. Frame Streams 帧编码（dnswire 核心能力）：用 dnswire_encoder_encode()
 *      编码一条 dnstap 消息并检查产生非零字节流。
 *
 * 口径：仅使用已安装/导出的公开头文件与公开 API，不触碰内部符号或
 * 库内部测试目录。业务意义：DNS 事件采集（dnstap）是递归解析器、
 * 中心化日志采集等上层组件的基础能力，本用例模拟上层组件在一次
 * 事件往返后拿到可解析的 protobuf 载荷并验证内容。
 */
#include <dnswire/dnswire.h>
#include <dnswire/dnstap.h>
#include <dnswire/version.h>
#include <dnswire/encoder.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                          \
    do {                                          \
        if (!(cond)) {                            \
            fprintf(stderr, "FAIL: %s\n", msg);   \
            failures++;                           \
        }                                         \
        else {                                    \
            printf("PASS: %s\n", msg);            \
        }                                         \
    } while (0)

int main(void)
{
    struct dnstap d = DNSTAP_INITIALIZER;
    static char identity[] = "ohos-dnswire-test";
    static char query_msg[] = "dns_wire_format_ohos_test";
    static unsigned char qaddr[4] = { 127, 0, 0, 1 };
    static unsigned char raddr[4] = { 8, 8, 8, 8 };

    /* 构造一条 TOOL_QUERY 事件（模拟上层 DNS 采集组件上报） */
    dnstap_set_identity_string(d, identity);
    dnstap_set_version_string(d, DNSWIRE_VERSION_STRING);
    dnstap_set_type(d, DNSTAP_TYPE_MESSAGE);
    dnstap_message_set_type(d, DNSTAP_MESSAGE_TYPE_TOOL_QUERY);
    dnstap_message_set_socket_family(d, DNSTAP_SOCKET_FAMILY_INET);
    dnstap_message_set_socket_protocol(d, DNSTAP_SOCKET_PROTOCOL_UDP);
    dnstap_message_set_query_address(d, qaddr, sizeof(qaddr));
    dnstap_message_set_query_port(d, 12345);
    dnstap_message_set_response_address(d, raddr, sizeof(raddr));
    dnstap_message_set_response_port(d, 53);
    dnstap_message_set_query_message(d, query_msg, sizeof(query_msg) - 1);

    /* 1) protobuf 编码往返 */
    size_t need = dnstap_encode_protobuf_size(&d);
    CHECK(need > 0, "dnstap_encode_protobuf_size() > 0");
    uint8_t* buf = (uint8_t*)malloc(need ? need : 1);
    CHECK(buf != NULL, "buffer alloc");
    size_t wrote = dnstap_encode_protobuf(&d, buf);
    CHECK(wrote == need, "dnstap_encode_protobuf() wrote == needed size");
    CHECK(wrote > 0, "encoded protobuf non-empty");

    struct dnstap d2 = DNSTAP_INITIALIZER;
    CHECK(dnstap_decode_protobuf(&d2, buf, wrote) == 0, "dnstap_decode_protobuf() ok");
    CHECK(dnstap_type(d2) == DNSTAP_TYPE_MESSAGE, "decoded type == MESSAGE");
    CHECK(dnstap_message_type(d2) == DNSTAP_MESSAGE_TYPE_TOOL_QUERY,
          "decoded message type == TOOL_QUERY");
    CHECK(dnstap_message_query_port(d2) == 12345, "decoded query_port == 12345");
    CHECK(dnstap_message_response_port(d2) == 53, "decoded response_port == 53");
    CHECK(dnstap_message_query_message_length(d2) == sizeof(query_msg) - 1,
          "decoded query_message length");
    CHECK(memcmp(dnstap_message_query_message(d2), query_msg,
                 sizeof(query_msg) - 1) == 0,
          "decoded query_message payload matches");
    /* identity/version are protobuf-c bytestrings (no NUL guarantee);
     * compare with length, not strcmp. */
    CHECK(dnstap_identity_length(d2) == strlen(identity) &&
              memcmp(dnstap_identity(d2), identity,
                     dnstap_identity_length(d2)) == 0,
          "decoded identity matches");
    CHECK(dnstap_version_length(d2) >= 5 &&
              memcmp(dnstap_version(d2), "0.5.0", 5) == 0,
          "decoded version starts with 0.5.0");
    dnstap_cleanup(&d2);
    free(buf);

    /* 2) 动态库公开符号（链接期已解析，运行期再验证一次探测函数） */
    CHECK(strcmp(dnswire_result_string[dnswire_ok], "ok") == 0,
          "dnswire_result_string[] exported and usable at runtime");

    /* 3) Frame Streams 编码（dnswire 核心传输封装）：
     * 编码器是状态机（control_ready→start→frames→…），每次调用写一段
     * 帧，返回 dnswire_again 表示继续、dnswire_ok 表示数据帧已写出，
     * dnswire_endofdata 表示对端 FIN。仿上游 writer 循环调用直至出帧。 */
    struct dnswire_encoder e = DNSWIRE_ENCODER_INITIALIZER;
    dnswire_encoder_set_dnstap(e, &d);
    uint8_t frame[8192];
    enum dnswire_result r = dnswire_again;
    int enc_iter = 0;
    while (r != dnswire_ok && r != dnswire_endofdata &&
           r != dnswire_error && enc_iter++ < 16) {
        r = dnswire_encoder_encode(&e, frame, sizeof(frame));
    }
    CHECK(r == dnswire_ok, "dnswire_encoder_encode() produced a data frame");
    CHECK(dnswire_encoder_encoded(e) > 0, "encoder produced bytes");

    dnstap_cleanup(&d);
    printf("dnswire version %s: OHOS-specific test %s\n",
           DNSWIRE_VERSION_STRING, failures ? "FAILED" : "PASSED");
    return failures ? 1 : 0;
}