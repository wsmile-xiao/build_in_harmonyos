// test_oscpack.cpp — 端到端消费者测试 (oscpack/1.1.0 on OHOS aarch64)
//
// 完整消费者工作流：用 oscpack 打包一条 OSC 消息与一个 bundle，
// 再把生成的字节流当作网络收到的包解析回来，逐项校验字段值。
// 同时校验 LP64 类型修复（sizeof(osc::int32)==4）与错误类型访问抛异常。
#include <cstdio>
#include <cstring>
#include <cstddef>

#include "osc/OscOutboundPacketStream.h"
#include "osc/OscPrintReceivedElements.h"
#include "osc/OscReceivedElements.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            ++g_failures;                                                  \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                  \
    } while (0)

int main() {
    // 0. LP64 sanity: int32 must be exactly 4 bytes (OHOS aarch64 fix)
    CHECK(sizeof(osc::int32) == 4);
    CHECK(sizeof(osc::uint32) == 4);
    CHECK(sizeof(osc::int64) == 8);

    // 1. Pack: bundle(time=1234) containing one message with 4 argument types
    char buffer[1024];
    std::memset(buffer, 0, sizeof(buffer));
    std::size_t packetSize = 0;
    {
        osc::OutboundPacketStream ps(buffer, sizeof(buffer));
        ps << osc::BeginBundle(1234)
           << osc::BeginMessage("/sensor/position")
           << (osc::int32)42 << 3.14f << "hello" << true
           << osc::EndMessage
           << osc::EndBundle;
        CHECK(ps.IsReady());
        CHECK(ps.Size() > 0);
        CHECK(ps.Size() % 4 == 0);  // OSC packets are 4-byte aligned
        packetSize = ps.Size();
    }

    // 2. Unpack the same bytes as if received from the network
    {
        osc::ReceivedBundle bundle(
            osc::ReceivedPacket(buffer, (osc::osc_bundle_element_size_t)packetSize));
        CHECK(bundle.TimeTag() == (osc::uint64)1234);
        CHECK(bundle.ElementsBegin() != bundle.ElementsEnd());

        osc::ReceivedMessage msg(*bundle.ElementsBegin());
        CHECK(std::strcmp(msg.AddressPattern(), "/sensor/position") == 0);

        osc::ReceivedMessageArgumentIterator arg = msg.ArgumentsBegin();
        CHECK(arg->IsInt32());
        CHECK(arg->AsInt32() == 42);
        ++arg;
        CHECK(arg->IsFloat());
        CHECK(arg->AsFloat() == 3.14f);
        ++arg;
        CHECK(arg->IsString());
        CHECK(std::strcmp(arg->AsString(), "hello") == 0);
        ++arg;
        CHECK(arg->IsBool());
        CHECK(arg->AsBool() == true);
        ++arg;
        CHECK(arg == msg.ArgumentsEnd());
    }

    // 3. Byte-order round trip of a distinctive int32 pattern
    {
        osc::OutboundPacketStream ps(buffer, sizeof(buffer));
        ps << osc::BeginMessage("/pattern") << (osc::int32)0x01020304 << osc::EndMessage;
        CHECK(ps.IsReady());
        CHECK(ps.Size() % 4 == 0);

        osc::ReceivedMessage msg(osc::ReceivedPacket(ps.Data(), (osc::osc_bundle_element_size_t)ps.Size()));
        CHECK(std::strcmp(msg.AddressPattern(), "/pattern") == 0);
        CHECK(msg.ArgumentsBegin()->AsInt32() == 0x01020304);
    }

    // 4. Wrong-type access must raise an osc::Exception (robustness contract)
    bool threw = false;
    try {
        osc::OutboundPacketStream ps(buffer, sizeof(buffer));
        ps << osc::BeginMessage("/b") << true << osc::EndMessage;
        osc::ReceivedMessage msg(osc::ReceivedPacket(ps.Data(), (osc::osc_bundle_element_size_t)ps.Size()));
        (void)msg.ArgumentsBegin()->AsInt32();  // bool is not int32
    } catch (osc::Exception &) {
        threw = true;
    }
    CHECK(threw);

    std::printf("%d checks run, %d passed, %d failed\n",
                g_checks, g_checks - g_failures, g_failures);
    return g_failures == 0 ? 0 : 1;
}
