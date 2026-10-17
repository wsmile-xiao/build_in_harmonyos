// test_package 消费者测试（R34：必须真实调用被测包 API，禁止 print-only 空壳）
// 验证 libftp 的 ftp::client 公共 API 可编译、链接并正确返回
// （网络无关的构造/设置/查询接口；真实 FTP 会话属上游集成测试范畴）。
#include <ftp/client.hpp>
#include <ftp/transfer_mode.hpp>
#include <ftp/transfer_type.hpp>

#include <cstdio>

int main() {
    // 1) 默认构造 ftp::client（被动模式 + 二进制传输）
    ftp::client client;

    // 2) 传输模式 setter/getter 往返
    client.set_transfer_mode(ftp::transfer_mode::active);
    if (client.get_transfer_mode() != ftp::transfer_mode::active) {
        std::fprintf(stderr, "FAIL: transfer_mode roundtrip (active)\n");
        return 1;
    }
    client.set_transfer_mode(ftp::transfer_mode::passive);
    if (client.get_transfer_mode() != ftp::transfer_mode::passive) {
        std::fprintf(stderr, "FAIL: transfer_mode roundtrip (passive)\n");
        return 1;
    }

    // 3) RFC2428 (EPSV/EPRT) 开关 setter/getter 往返
    client.set_rfc2428_support(false);
    if (client.get_rfc2428_support()) {
        std::fprintf(stderr, "FAIL: rfc2428_support roundtrip (false)\n");
        return 1;
    }
    client.set_rfc2428_support(true);
    if (!client.get_rfc2428_support()) {
        std::fprintf(stderr, "FAIL: rfc2428_support roundtrip (true)\n");
        return 1;
    }

    // 4) 未连接时 is_connected() 必须为 false
    if (client.is_connected()) {
        std::fprintf(stderr, "FAIL: is_connected() must be false before connect\n");
        return 1;
    }

    std::printf("test libftp 1.5.0: OK (client API roundtrips passed)\n");
    return 0;
}
