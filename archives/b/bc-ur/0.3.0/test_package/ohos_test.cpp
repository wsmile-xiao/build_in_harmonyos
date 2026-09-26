//
//  ohos_test.cpp — bc-ur 0.3.0 HarmonyOS 专项测试
//
//  在 OHOS PC（aarch64, musl libc + clang 15 / libc++）运行时环境验证库的
//  关键正确性属性（-Wall -Wextra -Werror 严格编译，杜绝隐式转换/未用变量）：
//    - crc32 已知向量：传输/完整性校验基石的精确字节输出
//    - Bytewords 最小编码/解码往返（UR 在 QR 场景的最小化编码路径）
//    - 256 KiB 大消息 fountain 分片流式解码（URDecoder 逐片 receive 恢复，
//      覆盖 OHOS 上大缓冲区 xor/crc 路径无截断或越界）
//  全部断言使用公开头 <bc-ur/bc-ur.hpp> 的公开 API；退出码 0 = 全部通过。
//

#include <bc-ur/bc-ur.hpp>

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

using namespace ur;

static int g_failures = 0;
#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);             \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

static ByteVector make_payload(size_t len) {
    ByteVector v(len);
    for (size_t i = 0; i < len; ++i) {
        v[i] = static_cast<uint8_t>((i * 13 + 7) & 0xff);
    }
    return v;
}

static UR make_bytes_ur(const ByteVector& payload) {
    ByteVector cbor;
    CborLite::encodeBytes(cbor, payload);
    return UR("bytes", cbor);
}

int main() {
    // 1) crc32 已知向量（与上游 test.cpp 同源断言：CRC-32 值必须是精确字节）
    CHECK(data_to_hex(crc32_bytes(string_to_bytes("Hello, world!"))) == "ebe6c6e6");
    CHECK(data_to_hex(crc32_bytes(string_to_bytes("Wolf"))) == "598c84dc");

    // 2) Bytewords minimal 风格往返（UR 二维码最小化路径）
    ByteVector input = {0, 1, 2, 128, 255};
    const std::string min_enc = Bytewords::encode(Bytewords::style::minimal, input);
    CHECK(min_enc == "aeadaolazmjendeoti");
    CHECK(Bytewords::decode(Bytewords::style::minimal, min_enc) == input);

    // 3) 256 KiB 大消息 fountain 流式解码往返（OHOS aarch64 上大缓冲区路径）
    const size_t kBigLen = 256 * 1024;
    ByteVector big = make_payload(kBigLen);
    UR big_ur = make_bytes_ur(big);
    UREncoder encoder(big_ur, 1500, 0);
    URDecoder decoder;
    size_t parts_sent = 0;
    while (!decoder.is_complete() && parts_sent < 512) {
        decoder.receive_part(encoder.next_part());
        ++parts_sent;
    }
    CHECK(parts_sent < 512);                 // 约 171 片内收齐，防死循环
    CHECK(decoder.expected_part_count() > 1); // 确为多分片传输
    CHECK(decoder.is_success());
    const ByteVector& recovered = decoder.result_ur().cbor();
    CHECK(recovered.size() > kBigLen);        // cbor 封装后大于原始载荷
    {
        // 解 cbor 外层还原原始 payload 并逐字节比对（CborLite 公开 API）
        ByteVector decoded_payload;
        auto pos = recovered.cbegin();
        CborLite::decodeBytes(pos, recovered.cend(), decoded_payload);
        CHECK(decoded_payload == big);
    }

    if (g_failures == 0) {
        std::printf("bc-ur ohos test: ALL PASSED\n");
        return 0;
    }
    std::printf("bc-ur ohos test: %d FAILURES\n", g_failures);
    return 1;
}