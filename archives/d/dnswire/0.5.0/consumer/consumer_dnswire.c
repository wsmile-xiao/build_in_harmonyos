/*
 * dnswire 消费者验证用例 (HarmonyOS PC)
 *
 * 模拟业务上层组件/应用使用该三方库：
 *   - 仅通过库已安装/导出的公开头文件（dnswire/dnswire.h、dnswire/dnstap.h、
 *     生成的 dnswire/dnstap.pb-c.h）与公开 API（dnstap_encode/decode_protobuf、
 *     dnswire_encoder_*、dnswire_reader/writer 之外的核心编解码）编译、链接、
 *     调用并正常运行；
 *   - 覆盖至少一个有业务意义的公开 API 调用及其可观察结果：本用例模拟
 *     DNS 事件采集器编码一条 dnstap 事件为 protobuf，再解码并核对字段，
 *     验证第三方使用者能完成编译、链接、运行的全链路。
 *   - 不包含库私有头文件、不调用内部符号、不复用库内部测试构建目录。
 */
#include <dnswire/dnswire.h>
#include <dnswire/dnstap.h>
#include <dnswire/version.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, const char* argv[])
{
    const char* identity = "consumer-app";
    if (argc > 1) {
        identity = argv[1];
    }

    struct dnstap d = DNSTAP_INITIALIZER;
    static const unsigned char qaddr[] = { 192, 0, 2, 1 };
    static const unsigned char raddr[] = { 198, 51, 100, 7 };

    /* 模拟上层解析器把一次客户端查询事件编码为 dnstap protobuf */
    dnstap_set_identity_string(d, identity);
    dnstap_set_version_string(d, DNSWIRE_VERSION_STRING);
    dnstap_set_type(d, DNSTAP_TYPE_MESSAGE);
    dnstap_message_set_type(d, DNSTAP_MESSAGE_TYPE_RESOLVER_QUERY);
    dnstap_message_set_socket_family(d, DNSTAP_SOCKET_FAMILY_INET);
    dnstap_message_set_socket_protocol(d, DNSTAP_SOCKET_PROTOCOL_UDP);
    dnstap_message_set_query_address(d, qaddr, sizeof(qaddr));
    dnstap_message_set_query_port(d, 5300);
    dnstap_message_set_response_address(d, raddr, sizeof(raddr));
    dnstap_message_set_response_port(d, 53);

    size_t need = dnstap_encode_protobuf_size(&d);
    if (need == 0) {
        fprintf(stderr, "consumer: encode size 0\n");
        return 1;
    }
    uint8_t* wire = (uint8_t*)malloc(need);
    size_t wrote = dnstap_encode_protobuf(&d, wire);
    if (wrote != need || wrote == 0) {
        fprintf(stderr, "consumer: encode failed\n");
        return 1;
    }

    /* 上层组件从传输通道收到 protobuf 载荷后解码 */
    struct dnstap d2 = DNSTAP_INITIALIZER;
    if (dnstap_decode_protobuf(&d2, wire, wrote) != 0) {
        fprintf(stderr, "consumer: decode failed\n");
        return 1;
    }
    int ok = (dnstap_message_type(d2) == DNSTAP_MESSAGE_TYPE_RESOLVER_QUERY) &&
             (dnstap_message_query_port(d2) == 5300) &&
             (dnstap_message_response_port(d2) == 53) &&
             (dnstap_identity_length(d2) == strlen(identity)) &&
             (memcmp(dnstap_identity(d2), identity,
                     dnstap_identity_length(d2)) == 0);

    printf("consumer: dnswire %s identity=%s query_port=%u -> response_port=%u %s\n",
           DNSWIRE_VERSION_STRING, identity,
           (unsigned)dnstap_message_query_port(d2),
           (unsigned)dnstap_message_response_port(d2),
           ok ? "OK" : "MISMATCH");

    dnstap_cleanup(&d2);
    dnstap_cleanup(&d);
    free(wire);
    return ok ? 0 : 1;
}