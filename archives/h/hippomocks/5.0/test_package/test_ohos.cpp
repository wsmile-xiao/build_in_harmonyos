// HarmonyOS 专项测试 (OHOS-specific test) — hippomocks 5.0.
// 独立于上游测试与消费者用例：验证在 OHOS aarch64 平台上
// (1) 虚拟函数打桩 (MockRepository) 可编译、链接、运行；
// (2) aarch64 下 CFUNC 打桩按适配补丁禁用后，库头文件在 OHOS 工具链下
//     仍可完整编译 (conflicting-types 修复回归)；
// (3) 返回公开 API 的可观察结果。
#include <hippomocks.h>

#include <cstdio>

class IDevice {
public:
    virtual ~IDevice() {}
    virtual int read() = 0;
    virtual int write(int v) = 0;
};

int main() {
#ifdef __OHOS__
    printf("OHOS platform build confirmed (__OHOS__)\n");
#endif
    MockRepository mocks;
    IDevice* dev = mocks.Mock<IDevice>();
    mocks.ExpectCall(dev, IDevice::read).Return(42);
    mocks.ExpectCall(dev, IDevice::write).With(7).Return(0);

    int r = dev->read();
    int w = dev->write(7);
    bool ok = (r == 42) && (w == 0);
    printf("ohos-special: read()=%d write()=%d -> %s\n", r, w, ok ? "PASS" : "FAIL");
    mocks.VerifyAll();
    return ok ? 0 : 1;
}