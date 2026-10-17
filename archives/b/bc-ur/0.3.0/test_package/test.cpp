//
//  test.cpp — bc-ur 0.3.0 消费者测试（Conan L1）
//
//  消费者用例：模拟业务上层组件，仅通过库已安装/导出的公开头文件
//  <bc-ur/bc-ur.hpp> 与公开 API 使用该库，验证第三方使用者能否
//  编译、链接、调用并正常运行：
//    - Bytewords::encode/decode        （校验已知向量的精确编码输出 + 往返）
//    - UREncoder::encode / URDecoder::decode（单部分 UR 编解码往返）
//    - UREncoder / URDecoder            （多部分 fountain 分片收齐恢复）
//  所有断言可观察、可复现；退出码 0 = 全部通过。
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
        v[i] = static_cast<uint8_t>((i * 7 + 3) & 0xff);
    }
    return v;
}

static UR make_bytes_ur(size_t len) {
    ByteVector cbor;
    CborLite::encodeBytes(cbor, make_payload(len));
    return UR("bytes", cbor);
}

int main() {
    // 1) Bytewords：公开 API 对已知向量产生精确编码并可往返解码
    ByteVector input = {0, 1, 2, 128, 255};
    const std::string enc1 = Bytewords::encode(Bytewords::style::standard, input);
    CHECK(enc1 == "able acid also lava zoom jade need echo taxi");
    CHECK(Bytewords::decode(Bytewords::style::standard, enc1) == input);

    // 2) 单部分 UR：UREncoder::encode → URDecoder::decode 往返一致
    UR ur = make_bytes_ur(50);
    const std::string encoded = UREncoder::encode(ur);
    CHECK(encoded.compare(0, 3, "ur:") == 0);
    UR decoded = URDecoder::decode(encoded);
    CHECK(decoded.type() == ur.type());
    CHECK(decoded.cbor() == ur.cbor());

    // 3) 多部分 UR（fountain 纠删编码）：顺序收片后解码恢复原始消息
    UR multipart = make_bytes_ur(32767);
    UREncoder encoder(multipart, 1000, 0);
    URDecoder decoder;
    size_t parts_sent = 0;
    while (!decoder.is_complete() && parts_sent < 64) {
        decoder.receive_part(encoder.next_part());
        ++parts_sent;
    }
    CHECK(parts_sent < 64);                  // 有限步内收齐（约 9-10 片）
    CHECK(decoder.is_success());
    CHECK(decoder.result_ur().cbor() == multipart.cbor());

    if (g_failures == 0) {
        std::printf("bc-ur consumer test: ALL PASSED\n");
        return 0;
    }
    std::printf("bc-ur consumer test: %d FAILURES\n", g_failures);
    return 1;
}