// ohos_specific_test.cpp — HarmonyOS 专项测试
// 覆盖 nameof 在 OHOS (aarch64-linux-ohos, clang 15) 平台的实际调用入口：
// NAMEOF / NAMEOF_TYPE / NAMEOF_ENUM / NAMEOF_MEMBER 编译期名称提取。
// 使用 OHOS SDK 工具链编译运行，验证 header-only 库在鸿蒙平台可用。
#include <nameof.hpp>
#include <cassert>
#include <iostream>

namespace ohos_ns {
enum class IoMode { Read, Write, Append };
struct Device {
    int fd = -1;
    const char* name = nullptr;
};
}  // namespace ohos_ns

int main() {
    // 1) 变量名
    int ohos_ret = 0;
    std::cout << "NAMEOF(ohos_ret)=" << NAMEOF(ohos_ret) << std::endl;
    assert(NAMEOF(ohos_ret) == "ohos_ret");

    // 2) 类型名（nameof 返回含命名空间的完全限定名）
    std::cout << "NAMEOF_TYPE=" << NAMEOF_TYPE(ohos_ns::Device) << std::endl;
    assert(std::string(NAMEOF_TYPE(ohos_ns::Device)) == "ohos_ns::Device");

    // 3) 枚举名
    std::cout << "NAMEOF_ENUM=" << NAMEOF(ohos_ns::IoMode::Write) << std::endl;
    assert(NAMEOF(ohos_ns::IoMode::Write) == "Write");

    // 4) 成员名（指针到成员语法）
    std::cout << "NAMEOF_MEMBER=" << NAMEOF_MEMBER(&ohos_ns::Device::fd) << std::endl;
    assert(NAMEOF_MEMBER(&ohos_ns::Device::fd) == "fd");

    // 5) 完整变量名（本编译环境返回末段成员名，与上游 NAMEOF_FULL(struct.somefield)=="somefield" 一致）
    ohos_ns::Device dev{};
    std::cout << "NAMEOF_FULL=" << NAMEOF_FULL(dev.name) << std::endl;
    assert(NAMEOF_FULL(dev.name) == "name");

    std::cout << "OHOS specific nameof test PASSED" << std::endl;
    return 0;
}