// thrift 0.22.0 的真实功能测试（R34 反空壳）：真调 API、真做计算、断言数值。
//
// 走 TBinaryProtocol 对一个结构体做「写 → 读」往返，断言逐字段还原。
// 刻意不只测「能编能链」——那三件事在没有 SONAME / 没装头 / 导出符号残缺的包上
// 同样会过（本仓已有 5 例这类缺陷，其中 4 例发生在 CI 全绿的已发布制品上）。
#include <thrift.h>
#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TBufferTransports.h>

#include <cstdio>
#include <cstring>
#include <string>

using apache::thrift::protocol::TBinaryProtocol;
using apache::thrift::transport::TMemoryBuffer;

static int failures = 0;

#define CHECK(cond, what)                                            \
    do {                                                             \
        if (!(cond)) {                                               \
            std::printf("FAIL: %s\n", (what));                       \
            ++failures;                                              \
        } else {                                                     \
            std::printf("ok  : %s\n", (what));                       \
        }                                                            \
    } while (0)

int main() {
    const int32_t   kCount  = 42;
    const int32_t   kDelta  = -7;
    const double    kRatio  = 2.5;
    const bool      kFlag   = true;
    const std::string kName = "thrift-roundtrip";

    // ---- 写 ----
    auto buf = std::make_shared<TMemoryBuffer>();
    TBinaryProtocol out(buf);
    uint32_t written = 0;
    written += out.writeMessageBegin(kName, apache::thrift::protocol::T_CALL, 1);
    written += out.writeI32(kCount);
    written += out.writeI32(kDelta);
    written += out.writeDouble(kRatio);
    written += out.writeBool(kFlag);
    written += out.writeString(kName);
    out.writeMessageEnd();
    out.getTransport()->flush();   // flush() 返回 void，不计入 written

    std::printf("written bytes = %u\n", written);
    CHECK(written > 0, "序列化产生了非空字节流");

    // ---- 读回 ----
    TBinaryProtocol in(buf);
    std::string rname;
    apache::thrift::protocol::TMessageType mtype;
    int32_t seqid = 0;
    in.readMessageBegin(rname, mtype, seqid);
    int32_t rcount = 0, rdelta = 0;
    double  rratio = 0.0;
    bool    rflag  = false;
    std::string rstr;
    in.readI32(rcount);
    in.readI32(rdelta);
    in.readDouble(rratio);
    in.readBool(rflag);
    in.readString(rstr);
    in.readMessageEnd();

    // ---- 断言 ----
    CHECK(rname  == kName,           "协议名往返一致");
    CHECK(seqid  == 1,               "seqid 往返一致");
    CHECK(mtype  == apache::thrift::protocol::T_CALL, "消息类型往返一致");
    CHECK(rcount == kCount,          "int32 正向值往返一致");
    CHECK(rdelta == kDelta,          "int32 负向值往返一致（补码编码）");
    CHECK(rratio == kRatio,          "double 往返精确一致");
    CHECK(rflag  == kFlag,           "bool 往返一致");
    CHECK(rstr   == kName,           "string 往返一致");

    // 消息类型枚举本身也是链接进来的常量，顺带钉住它没被裁掉
    CHECK(apache::thrift::protocol::T_REPLY != apache::thrift::protocol::T_CALL,
          "TMessageType 枚举常量可用且互异");

    if (failures) {
        std::printf("thrift: %d 项断言失败\n", failures);
        return 1;
    }
    std::printf("thrift: 全部断言通过\n");
    return 0;
}
