// test.cpp — lurlparser 1.1 消费者测试（仅经公开头文件与公开 API）。
//
// 模拟业务上层组件：只通过包安装/导出的公开头 LUrlParser.h 与公开 API
// (LUrlParser::ParseURL::parseURL / scheme_ / host_ / port_ / path_ /
// query_ / fragment_ / userName_ / password_ / isValid / getPort) 解析
// 真实 URL 并核验各字段，验证第三方使用者可编译、链接、调用并正常运行。
#include <cassert>
#include <cstdio>
#include <string>

#include "LUrlParser.h"

int main() {
    // 带 user:password、端口、path、query、fragment 的完整 URL
    const std::string url =
        "https://John:Dow@github.com:8080/corporateshark/LUrlParser/?a=1&b=2#frag";
    const LUrlParser::ParseURL parsed = LUrlParser::ParseURL::parseURL(url);

    if (!parsed.isValid()) {
        printf("FAIL: parseURL(%s) invalid\n", url.c_str());
        return 1;
    }
    if (parsed.scheme_ != "https" || parsed.host_ != "github.com" ||
        parsed.port_ != "8080" ||
        parsed.path_ != "corporateshark/LUrlParser/" ||
        parsed.query_ != "a=1&b=2" || parsed.fragment_ != "frag" ||
        parsed.userName_ != "John" || parsed.password_ != "Dow") {
        printf("FAIL: field mismatch\n  scheme=%s host=%s port=%s path=%s "
               "query=%s fragment=%s user=%s pass=%s\n",
               parsed.scheme_.c_str(), parsed.host_.c_str(),
               parsed.port_.c_str(), parsed.path_.c_str(),
               parsed.query_.c_str(), parsed.fragment_.c_str(),
               parsed.userName_.c_str(), parsed.password_.c_str());
        return 1;
    }

    // getPort：公开辅助 API，端口转 int 并校验 1..65535
    int port = 0;
    if (!parsed.getPort(&port) || port != 8080) {
        printf("FAIL: getPort() -> %d (expected 8080)\n", port);
        return 1;
    }

    printf("lurlparser consumer test PASSED: %s\n", url.c_str());
    return 0;
}
