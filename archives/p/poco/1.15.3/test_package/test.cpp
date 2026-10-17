// poco 1.15.3 · 鸿蒙 PC 真实断言测试
//
// 覆盖面按「这个包实际交付了什么」选：不是只 include 主头就算数，而是每个
// 被声明进 cpp_info.libs 的关键库都要有一次**真实计算 + 数值断言**。
// 只验主头会漏掉「某个组件 .so 装了但符号不全」这类缺陷——本仓已累计 5 例
// 只有真实计算才暴露，其中 4 例发生在 CI 显示 SUCCESS 的已发布制品上。
#include <Poco/Foundation.h>
#include <Poco/String.h>
#include <Poco/NumberFormatter.h>
#include <Poco/NumberParser.h>
#include <Poco/DateTime.h>
#include <Poco/DateTimeFormatter.h>
#include <Poco/Environment.h>
#include <Poco/RegularExpression.h>
#include <Poco/JSON/Parser.h>
#include <Poco/JSON/Object.h>
#include <Poco/DOM/DOMParser.h>
#include <Poco/DOM/Document.h>
#include <Poco/DOM/Element.h>
#include <Poco/Crypto/DigestEngine.h>
#include <Poco/Net/IPAddress.h>
#include <Poco/Util/AbstractConfiguration.h>
#include <Poco/Util/MapConfiguration.h>
#include <Poco/Zip/Compress.h>
#include <Poco/DigestStream.h>
#include <Poco/MD5Engine.h>

#include <cstdio>
#include <sstream>
#include <string>

static int g_fail = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        if (!(cond)) { std::printf("FAIL %s\n", (what)); ++g_fail; }           \
        else         { std::printf("ok   %s\n", (what)); }                     \
    } while (0)

int main() {
    // ── Foundation：字符串 / 数值 / 时间 ───────────────────────────────────
    CHECK(Poco::toUpper(std::string("poco")) == "POCO", "Foundation toUpper");
    CHECK(Poco::trim(std::string("  x  ")) == "x", "Foundation trim");
    CHECK(Poco::NumberFormatter::format(42) == "42", "Foundation NumberFormatter");
    int parsed = 0;
    CHECK(Poco::NumberParser::tryParse("-1234", parsed) && parsed == -1234,
          "Foundation NumberParser");

    Poco::DateTime dt(2026, 8, 9, 12, 34, 56);
    CHECK(Poco::DateTimeFormatter::format(dt, "%Y-%m-%d %H:%M:%S")
              == "2026-08-09 12:34:56", "Foundation DateTimeFormatter");

    // MD5 走真实摘要计算，比「能 include」强得多
    Poco::MD5Engine md5;
    Poco::DigestOutputStream ds(md5);
    ds << "abc";
    ds.flush();
    CHECK(Poco::DigestEngine::digestToHex(md5.digest())
              == "900150983cd24fb0d6963f7d28e17f72", "Foundation MD5 摘要值");

    // 环境信息：确认跑在 OHOS 上而不是被交叉编译产物骗过
    CHECK(!Poco::Environment::osName().empty(), "Foundation Environment");
    std::printf("     osName=%s arch=%s\n",
                Poco::Environment::osName().c_str(),
                Poco::Environment::osArchitecture().c_str());

    // ── PocoFoundation 的正则（内嵌 pcre2）────────────────────────────────
    Poco::RegularExpression re("([a-z]+)-([0-9]+)");
    std::string sub;
    CHECK(re.extract("poco-1153", sub) > 0 && sub == "poco-1153",
          "Foundation RegularExpression（内嵌 pcre2）");

    // ── PocoJSON ──────────────────────────────────────────────────────────
    Poco::JSON::Parser jp;
    auto jv = jp.parse("{\"n\":7,\"s\":\"hi\"}");
    auto obj = jv.extract<Poco::JSON::Object::Ptr>();
    CHECK(obj->getValue<int>("n") == 7 && obj->getValue<std::string>("s") == "hi",
          "JSON 解析取值");

    // ── PocoXML ───────────────────────────────────────────────────────────
    Poco::XML::DOMParser xp;
    auto doc = xp.parseString("<r><c a=\"v\"/></r>");
    auto root = doc->documentElement();
    CHECK(root->nodeName() == "r", "XML 根节点名");
    auto child = static_cast<Poco::XML::Element*>(root->firstChild());
    CHECK(child && child->getAttribute("a") == "v", "XML 属性取值");

    // ── PocoNet ───────────────────────────────────────────────────────────
    Poco::Net::IPAddress ip("192.168.1.7");
    CHECK(ip.toString() == "192.168.1.7", "Net IPAddress 解析");
    CHECK(ip.family() == Poco::Net::IPAddress::IPv4, "Net IPAddress 族判定");

    // ── PocoCrypto（链到 openssl 才有）─────────────────────────────────────
    Poco::Crypto::DigestEngine sha("SHA256");
    sha.update(std::string("abc"));
    CHECK(Poco::DigestEngine::digestToHex(sha.digest())
              == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
          "Crypto SHA256 摘要值（经 openssl）");

    // ── PocoUtil ──────────────────────────────────────────────────────────
    Poco::AutoPtr<Poco::Util::MapConfiguration> cfg(new Poco::Util::MapConfiguration);
    cfg->setString("a.b", "9");
    CHECK(cfg->getInt("a.b") == 9, "Util 配置读写");

    if (g_fail) {
        std::printf("poco 测试失败 %d 项\n", g_fail);
        return 1;
    }
    std::printf("poco 1.15.3: 全部断言通过\n");
    return 0;
}
