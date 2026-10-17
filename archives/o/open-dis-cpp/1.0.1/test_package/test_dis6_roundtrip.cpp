// test_dis6_roundtrip.cpp — test_package 消费者用例（DIS6 协议库）
//
// 通过 Conan 打包安装后的 OpenDIS6 真实公共 API 做序列化回环：
//   1) DIS::DataStream 基本读写回环（BIG = DIS 协议网络字节序）
//   2) DIS::EntityStatePdu marshal()/unmarshal() 回环 + 字段级核对
// 返回 0 = 全部断言通过；任一断言失败返回 1。
#include <cstdio>

#include <dis6/EntityID.h>
#include <dis6/EntityStatePdu.h>
#include <dis6/Vector3Double.h>
#include <dis6/utils/DataStream.h>

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
    const unsigned int magic = 0x44495321u;  // "DIS!"
    const float x = 12.5f;
    out << magic << x;
    check(!out.empty(), "DataStream 写入后非空");
    check(out.size() == sizeof(magic) + sizeof(x), "DataStream 字节数 == 写入长度");

    DIS::DataStream in(&out[0], out.size(), out.GetStreamEndian());
    unsigned int magic_in = 0;
    float x_in = 0.0f;
    in >> magic_in >> x_in;
    check(magic_in == magic, "uint32 回环值一致");
    check(x_in == x, "float 回环值一致");

    // ---- 2. EntityStatePdu marshal/unmarshal 回环 ----
    DIS::EntityStatePdu src;
    DIS::EntityID id;
    id.setSite(7);
    id.setApplication(3);
    id.setEntity(42);
    src.setEntityID(id);
    src.setForceId(1);
    src.setEntityAppearance(0x00000010);

    DIS::Vector3Double loc;
    loc.setX(11.5);
    loc.setY(-22.25);
    loc.setZ(3.75);
    src.setEntityLocation(loc);
    // 上游惯用法（test/PduUtils.cpp InitPDU 同款）：Pdu::_length 只在 unmarshal() 时回填，
    // 内存构造的 PDU 要先 setLength() 才能与回环后的副本做 operator== 比较
    src.setLength(static_cast<unsigned short>(src.getMarshalledSize()));

    DIS::DataStream pdu_stream(DIS::BIG);
    src.marshal(pdu_stream);
    check(!pdu_stream.empty(), "EntityStatePdu marshal 产出非空字节流");
    check(static_cast<int>(pdu_stream.size()) == src.getMarshalledSize(),
          "字节流长度 == PDU 报头声明的 marshalled size");

    DIS::EntityStatePdu copy;
    copy.unmarshal(pdu_stream);
    check(copy.getEntityID().getSite() == 7, "实体 ID site 字段回环");
    check(copy.getEntityID().getApplication() == 3, "实体 ID application 字段回环");
    check(copy.getEntityID().getEntity() == 42, "实体 ID entity 字段回环");
    check(copy.getForceId() == 1, "forceId 字段回环");
    check(copy.getEntityAppearance() == 0x00000010, "entityAppearance 字段回环");
    check(copy.getEntityLocation().getX() == 11.5, "位置 X 字段回环");
    check(copy.getEntityLocation().getY() == -22.25, "位置 Y 字段回环");
    check(copy.getEntityLocation().getZ() == 3.75, "位置 Z 字段回环");
    check(pdu_stream.GetReadPos() == pdu_stream.GetWritePos(), "回环读取后字节流已读尽");
    check(copy == src, "EntityStatePdu operator== 整体判定一致");

    std::printf("RESULT=%s checks=%d failed=%d\n",
                g_failed == 0 ? "ALL PASSED" : "FAILED", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
