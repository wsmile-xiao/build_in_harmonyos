// test_alicloud.cpp — 编译链接验证：实例化 MNSClient 验证符号链接（R34）
#include <mns/mns_client.h>
#include <cstdio>

int main() {
    // 实例化 MNSClient 验证构造函数与符号链接可用（不发起网络请求）
    mns::sdk::MNSClient client("http://localhost", "test-access-id", "test-access-key");
    (void)client;
    printf("alicloud (MNS C++ SDK) link OK: mns::MNSClient instantiated\n");
    return 0;
}
