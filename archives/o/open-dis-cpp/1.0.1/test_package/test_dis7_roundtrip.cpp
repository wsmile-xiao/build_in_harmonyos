// test_dis7_roundtrip.cpp — test_package 消费者用例（DIS7 协议库）
//
// 通过 Conan 打包安装后的 OpenDIS7 真实公共 API 做序列化回环：
//   1) DIS::DataStream 基本读写回环（BIG = DIS 协议网络字节序）
//   2) DIS::EntityStatePdu marshal()/unmarshal() 回环 + 字段级核对
// 与 DIS6 库类同名不同布局，必须单独链接 open-dis-cpp::dis7（见 conanfile.py package_info）。
// 返回 0 = 全部断言通过；任一断言失败返回 1。
#include <cstdio>

#include <dis7/EntityID.h>
#include <dis7/EntityStatePdu.h>
#include <dis7/SimulationAddress.h>
#include <dis7/Vector3Double.h>
#include <dis7/utils/DataStream.h>

static int g_checks = 0;
static int g_failed = 0;

static void check(bool ok, const char* what) {
    ++g_checks;
    if (ok) {
        std::printf("[ok]   %s\n", what);
    } else {
        ++g_failed;
        std::printf("[FAIL] %s\n", what);
    }
}

int main() {
    // ---- 1. DataStream 回环 ----
    DIS::DataStream out(DIS::BIG);
    const long long ticket = 0x1122334455667788LL;
    const short channel = -1234;
    out << ticket << channel;
    check(!out.empty(), "DataStream 写入后非空");
    check(out.size() == sizeof(ticket) + sizeof(channel), "DataStream 字节数 == 写入长度");

    DIS::DataStream in(&out[0], out.size(), out.GetStreamEndian());
    long long ticket_in = 0;
    short channel_in = 0;
    in >> ticket_in >> channel_in;
    check(ticket_in == ticket, "int64 回环值一致");
    check(channel_in == channel, "int16 回环值一致");

    // ---- 2. EntityStatePdu marshal/unmarshal 回环 ----
    DIS::EntityStatePdu src;
    DIS::EntityID id;
    DIS::SimulationAddress addr;
    addr.setSite(9);
    addr.setApplication(5);
    id.setSimulationAddress(addr);
    id.setEntityNumber(1234);
    src.setEntityID(id);
    src.setForceId(2);

    DIS::Vector3Double loc;
    loc.setX(-100.75);
    loc.setY(200.5);
    loc.setZ(0.125);
    src.setEntityLocation(loc);
    // 上游惯用法（PduSuperclass::_length 只在 unmarshal() 时回填）：
    // 内存构造的 PDU 先 setLength() 才能与回环后的副本做 operator== 比较
    src.setLength(static_cast<unsigned short>(src.getMarshalledSize()));

    DIS::DataStream pdu_stream(DIS::BIG);
    src.marshal(pdu_stream);
    check(!pdu_stream.empty(), "EntityStatePdu marshal 产出非空字节流");
    check(static_cast<int>(pdu_stream.size()) == src.getMarshalledSize(),
          "字节流长度 == PDU 报头声明的 marshalled size");

    DIS::EntityStatePdu copy;
    copy.unmarshal(pdu_stream);
    check(copy.getEntityID().getEntityNumber() == 1234, "实体编号字段回环");
    check(copy.getEntityID().getSimulationAddress().getSite() == 9, "仿真地址 site 字段回环");
    check(copy.getEntityID().getSimulationAddress().getApplication() == 5, "仿真地址 application 字段回环");
    check(copy.getForceId() == 2, "forceId 字段回环");
    check(copy.getEntityLocation().getX() == -100.75, "位置 X 字段回环");
    check(copy.getEntityLocation().getY() == 200.5, "位置 Y 字段回环");
    check(copy.getEntityLocation().getZ() == 0.125, "位置 Z 字段回环");
    check(pdu_stream.GetReadPos() == pdu_stream.GetWritePos(), "回环读取后字节流已读尽");
    check(copy == src, "EntityStatePdu operator== 整体判定一致");

    std::printf("RESULT=%s checks=%d failed=%d\n",
                g_failed == 0 ? "ALL PASSED" : "FAILED", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
