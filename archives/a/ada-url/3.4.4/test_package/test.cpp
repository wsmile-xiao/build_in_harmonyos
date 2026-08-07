/* test_package/test.cpp — ada-url 消费者测试
   验证可链接 libada.a 并调用 ada::parse 解析 URL。
*/
#include <ada.h>
#include <stdio.h>

int main(void) {
    auto url = ada::parse("https://example.com/path/to/page?q=hello#section");
    if (!url) {
        fprintf(stderr, "FAIL: ada::parse returned null\n");
        return 1;
    }
    if (url->get_protocol() != "https:") {
        fprintf(stderr, "FAIL: protocol mismatch (got %s)\n", std::string(url->get_protocol()).c_str());
        return 1;
    }
    if (url->get_host() != "example.com") {
        fprintf(stderr, "FAIL: host mismatch (got %s)\n", std::string(url->get_host()).c_str());
        return 1;
    }
    if (url->get_pathname() != "/path/to/page") {
        fprintf(stderr, "FAIL: pathname mismatch (got %s)\n", std::string(url->get_pathname()).c_str());
        return 1;
    }
    printf("ada URL parse: PASS (https://example.com/path/to/page?q=hello#section)\n");
    printf("  protocol: %s\n", std::string(url->get_protocol()).c_str());
    printf("  host:     %s\n", std::string(url->get_host()).c_str());
    printf("  pathname: %s\n", std::string(url->get_pathname()).c_str());
    printf("  search:   %s\n", std::string(url->get_search()).c_str());
    printf("  hash:     %s\n", std::string(url->get_hash()).c_str());
    return 0;
}