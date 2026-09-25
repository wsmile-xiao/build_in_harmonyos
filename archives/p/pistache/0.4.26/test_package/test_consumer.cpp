// pistache 消费者测试 —— 真实调用被测库的公共 API（R34）。
//
// 设计约束：全部断言均为纯计算路径，不绑定端口、不启动服务，因此在沙箱/CI 环境下
// 也是确定性的；同时覆盖头文件可解析、符号可链接、运行期可执行三层验证。
#include <pistache/endpoint.h>
#include <pistache/http.h>
#include <pistache/net.h>

#include <iostream>
#include <string>

namespace {

int checks = 0;
int failed = 0;

void expect(bool condition, const char* what)
{
    ++checks;
    if (!condition)
    {
        ++failed;
        std::cerr << "FAIL: " << what << "\n";
    }
}

} // namespace

int main()
{
    // 1) Uri::Query —— 查询串构造与取值，纯计算
    Pistache::Http::Uri::Query query{{"alpha", "1"}, {"beta", "two"}};
    expect(query.has("alpha"), "query.has(alpha)");
    expect(query.has("beta"), "query.has(beta)");
    expect(!query.has("gamma"), "query.has(gamma) is false");
    expect(query.get("alpha").value_or("") == "1", "query.get(alpha) == \"1\"");
    expect(query.get("beta").value_or("") == "two", "query.get(beta) == \"two\"");
    expect(query.as_str().find("alpha=1") != std::string::npos, "query.as_str() contains alpha=1");

    // 2) Address / IP / Port —— 地址对象构造，不绑定、不监听
    Pistache::Address address(Pistache::IP::any(), Pistache::Port(8080));
    expect(static_cast<uint16_t>(address.port()) == 8080, "address.port() == 8080");
    expect(!address.host().empty(), "address.host() is non-empty");

    // 3) Endpoint —— 构造（不调用 init()/start()，不占用端口）
    Pistache::Http::Endpoint endpoint(address);
    expect(true, "Endpoint constructed from Address");

    // 4) 版本枚举可区分
    expect(Pistache::Http::Version::Http11 != Pistache::Http::Version::Http10,
           "Http11 != Http10");

    std::cout << "pistache consumer: checks=" << checks << " failed=" << failed << "\n";
    return failed == 0 ? 0 : 1;
}
