// consumer_cpp.cpp — 消费者验证（C++ API，业务上层组件视角）
// 仅使用 libvpd 公开头文件 (libvpd-2/system.hpp) 与公开 C++ API，通过正常
// 链接目标 (libvpd_cxx) 编译链接并运行；调用有业务意义的公开 API：
// lsvpd::System 序列化 pack()/unpack() 往返 + getMachineType()/getSerial1()
// 取值一致性，结果可观察（非空打包缓冲 + 往返相等断言）。
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <libvpd-2/system.hpp>

int main()
{
    lsvpd::System sys;
    void *buf = nullptr;
    unsigned int len = sys.pack(&buf);
    if (len == 0 || buf == nullptr) {
        std::fprintf(stderr, "consumer_cpp: FAIL pack() empty\n");
        return 1;
    }

    lsvpd::System unpacked;
    unpacked.unpack(buf);
    delete[] static_cast<char *>(buf);

    if (unpacked.getMachineType() != sys.getMachineType()) {
        std::fprintf(stderr, "consumer_cpp: FAIL round-trip machineType\n");
        return 1;
    }
    if (unpacked.getSerial1() != sys.getSerial1()) {
        std::fprintf(stderr, "consumer_cpp: FAIL round-trip serial1\n");
        return 1;
    }

    std::printf("consumer_cpp: pack/unpack round-trip OK (%u bytes, machineType='%s', serial1='%s')\n",
                len, unpacked.getMachineType().c_str(), unpacked.getSerial1().c_str());
    return 0;
}