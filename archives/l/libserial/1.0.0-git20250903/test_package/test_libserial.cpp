// LibSerial 1.0.0 消费者冒烟测试（无需串口硬件）。
// 断言与上游 test/unit_tests.cpp 的无硬件用例同源：
//   - 默认构造后处于关闭状态（SerialPort/SerialStream/SerialStreamBuf）
//   - 未打开端口调用 API 抛 NotOpen
//   - 打开不存在的设备抛 OpenFailed，且保持关闭状态
#include <cstdlib>
#include <iostream>

#include <libserial/SerialPort.h>
#include <libserial/SerialStream.h>
#include <libserial/SerialStreamBuf.h>

namespace {

int gFailures = 0;

void Check(bool ok, const char* what)
{
    if (ok) {
        std::cout << "PASS: " << what << "\n";
    } else {
        std::cerr << "FAIL: " << what << "\n";
        ++gFailures;
    }
}

} // namespace

int main()
{
    LibSerial::SerialPort serialPort;

    Check(!serialPort.IsOpen(), "SerialPort default state is closed");

    bool notOpenThrown = false;
    try {
        serialPort.SetBaudRate(LibSerial::BaudRate::BAUD_115200);
    } catch (const LibSerial::NotOpen&) {
        notOpenThrown = true;
    } catch (...) {
        notOpenThrown = false;
    }
    Check(notOpenThrown, "SetBaudRate on closed port throws NotOpen");

    bool openFailedThrown = false;
    try {
        serialPort.Open("/dev/serial_port_nonexistent_for_test");
    } catch (const LibSerial::OpenFailed&) {
        openFailedThrown = true;
    } catch (...) {
        openFailedThrown = false;
    }
    Check(openFailedThrown, "Open on nonexistent device throws OpenFailed");
    Check(!serialPort.IsOpen(), "SerialPort stays closed after failed Open");

    LibSerial::SerialStream serialStream;
    Check(!serialStream.IsOpen(), "SerialStream default state is closed");

    bool streamOpenFailed = false;
    try {
        serialStream.Open("/dev/some_non_existent_device_hope_it_does_not_exist");
    } catch (const LibSerial::OpenFailed&) {
        streamOpenFailed = true;
    } catch (...) {
        streamOpenFailed = false;
    }
    Check(streamOpenFailed, "SerialStream::Open on nonexistent device throws OpenFailed");
    Check(!serialStream.good(), "SerialStream not good after failed Open");

    LibSerial::SerialStreamBuf streamBuf;
    Check(!streamBuf.IsOpen(), "SerialStreamBuf default state is closed");

    if (gFailures == 0) {
        std::cout << "ALL PASS (8 checks)\n";
        return EXIT_SUCCESS;
    }
    std::cerr << gFailures << " check(s) failed\n";
    return EXIT_FAILURE;
}
