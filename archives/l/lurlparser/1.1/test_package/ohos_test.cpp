// ohos_test.cpp — lurlparser 1.1 HarmonyOS 专项测试。
//
// 验证与 OHOS aarch64 平台相关的真实行为（区别于上游 gtest 测试与
// 消费者 test.cpp）：
//   1) -Werror 严格编译：本文件在 OHOS clang 工具链下以 -Wall -Wextra
//      -Werror 编译（见 CMakeLists），直接验证公开头 LUrlParser.h 在
//      OHOS 上零告警成立。
//   2) IPv6 字面主机名（带 []）解析 + 端口分离。
//   3) getPort 端口范围校验边界：0、65535 合法上限、65536 越界。
//   4) 无端口 URL、无 path 的 authority-only URL 解析。
#include <cassert>
#include <cstdio>
#include <string>

#include "LUrlParser.h"

static int check_port(const std::string& url, bool expect_valid, int expect_port) {
    const LUrlParser::ParseURL p = LUrlParser::ParseURL::parseURL(url);
    if (!p.isValid()) {
        printf("FAIL: %s invalid\n", url.c_str());
        return 1;
    }
    int port = -1;
    const bool ok = p.getPort(&port);
    if (ok != expect_valid || (expect_valid && port != expect_port)) {
        printf("FAIL: %s getPort ok=%d port=%d (expect ok=%d port=%d)\n",
               url.c_str(), ok ? 1 : 0, port, expect_valid ? 1 : 0, expect_port);
        return 1;
    }
    return 0;
}

int main() {
    // 2) IPv6 主机名（OHOS 网络栈常见形态）
    {
        const LUrlParser::ParseURL p = LUrlParser::ParseURL::parseURL(
            "https://[fe80::9a01:a7ff:feb1:7dc9]:8443/api/v1");
        if (!p.isValid() || p.host_ != "[fe80::9a01:a7ff:feb1:7dc9]" ||
            p.port_ != "8443" || p.path_ != "api/v1") {
            printf("FAIL: IPv6 host parse\n");
            return 1;
        }
        int port = 0;
        if (!p.getPort(&port) || port != 8443) {
            printf("FAIL: IPv6 getPort -> %d\n", port);
            return 1;
        }
    }

    // 3) 端口范围边界：0 非法；65535 合法上限；65536 越界非法
    if (check_port("http://foo.com:0/", false, 0)) return 1;
    if (check_port("http://foo.com:65535/", true, 65535)) return 1;
    if (check_port("http://foo.com:65536/", false, 0)) return 1;

    // 4) 无端口 URL / authority-only URL
    {
        const LUrlParser::ParseURL p = LUrlParser::ParseURL::parseURL(
            "https://example.com");
        if (!p.isValid() || p.host_ != "example.com" || !p.port_.empty() ||
            !p.path_.empty()) {
            printf("FAIL: authority-only URL\n");
            return 1;
        }
        int port = -1;
        if (p.getPort(&port)) {  // 无端口 -> getPort 应返回 false
            printf("FAIL: no-port getPort should be false\n");
            return 1;
        }
    }

    printf("lurlparser OHOS test PASSED: IPv6 host, port bounds, authority-only\n");
    return 0;
}
