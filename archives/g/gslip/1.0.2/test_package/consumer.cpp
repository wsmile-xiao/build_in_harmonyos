/* 消费者测试：以库使用者身份调用 libgslip 公开 API（R34）。
 * 初始化 SLIP 存储子系统 → 分配 LONG 型 SlipDatum → 通过
 * operator LONG() 读回 → 断言值一致；任一断言失败即非零退出。
 */
#include <gslip/Slip.h>
#include <gslip/SlipDatum.h>

#include <cstdio>

using namespace slip;

int main() {
    slipInit(1024, 128);

    SlipDatum* datum = new SlipDatum((LONG)0x15);
    LONG value = (LONG)(*datum);
    delete datum;

    bool ok = (value == (LONG)0x15);
    std::printf("gslip consumer: %s (value=0x%lx)\n",
                ok ? "OK" : "FAIL", (unsigned long)value);
    return ok ? 0 : 1;
}
