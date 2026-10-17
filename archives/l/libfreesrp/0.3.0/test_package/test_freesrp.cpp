#include <freesrp.hpp>

#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        ++checks;                                                            \
        if (cond) {                                                          \
            std::printf("PASS: %s\n", (msg));                                \
        } else {                                                             \
            std::printf("FAIL: %s\n", (msg));                                \
            ++failures;                                                      \
        }                                                                    \
    } while (0)

int main() {
    // A1/A2: 上游协议常量（USB VID/PID）在 OHOS 交叉编译下保持原值
    CHECK(FREESRP_VENDOR_ID == 0xe1ec, "FREESRP_VENDOR_ID == 0xe1ec");
    CHECK(FREESRP_PRODUCT_ID == 0xf5d0, "FREESRP_PRODUCT_ID == 0xf5d0");

    // A3: 协议帧参数与超时常量
    CHECK(FREESRP_BYTES_PER_SAMPLE == 4, "FREESRP_BYTES_PER_SAMPLE == 4");
    CHECK(FREESRP_USB_TIMEOUT == 4000, "FREESRP_USB_TIMEOUT == 4000");

    // A4: ConnectionError 异常类型派生关系（消费者可直接 catch）
    CHECK((std::is_base_of<std::runtime_error, FreeSRP::ConnectionError>::value),
          "FreeSRP::ConnectionError derives from std::runtime_error");

    // A5: freesrp_version 结构体可通过 operator<< 流式输出（ABI/头文件完整性）
    FreeSRP::freesrp_version v;
    v.fx3 = "0.0.0-test";
    v.fpga = "0.0.0-test";
    std::ostringstream oss;
    oss << v;
    CHECK(!oss.str().empty() && oss.str().find("0.0.0-test") != std::string::npos,
          "freesrp_version streamable via operator<<");

    // A6/A7: list_connected() 在无 FreeSRP 硬件环境下的安全行为——
    // libusb 初始化+设备枚举路径真实执行：要么返回空列表，要么抛 ConnectionError
    bool offline_ok = false;
    std::string detail;
    try {
        std::vector<std::string> list = FreeSRP::FreeSRP::list_connected();
        offline_ok = list.empty();
        detail = "returned empty list (no FreeSRP hardware attached)";
    } catch (FreeSRP::ConnectionError &e) {
        offline_ok = true;
        detail = std::string("threw ConnectionError as expected: ") + e.what();
    }
    CHECK(offline_ok, "list_connected() safe offline");
    std::printf("INFO: list_connected detail: %s\n", detail.c_str());
    std::printf("RESULT: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
