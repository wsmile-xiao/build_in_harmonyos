// Consumer test for webforcpp 0.2.0 — exercises real APIs (R34 compliant)
#undef NDEBUG
#include <cassert>
#include <iostream>
#include <string>

// Core headers
#include "webforcpp/json.hpp"
#include "webforcpp/https.hpp"
#include "webforcpp/http.hpp"
#include "webforcpp/utils.hpp"

int main() {
    using namespace web::json;
    using namespace web;

    // 1) JSON parsing (mirrors upstream test/json.cpp)
    {
        const ast_t ast;
        char text[] = R"({"name":"test","value":2})";
        const auto& doc = parse(*ast, make_view(text));
        assert(doc.is_valid());
        const auto& root = *doc;
        assert(root.is_object());
        const auto& name = root("name");
        assert(name.is_string());
        assert(name.to_string() == "test");
        std::cout << "json parse OK: " << name.to_string() << std::endl;
    }

    // 2) JSON building helpers
    {
        const spec_t spec = {"name", "age", "dead"};
        auto out = make_json(spec, "David", 20, false);
        assert(out == R"({"name":"David","age":20,"dead":false})");
        auto arr = make_array(spec, false);
        assert(arr == R"(["name","age","dead"])");
        std::cout << "json build OK: " << out << std::endl;
    }

    // 3) utils — net_address and url helpers (mirrors upstream test/https.cpp)
    {
        auto addr = net_address("127.0.0.1");
        assert(*addr == "127.0.0.1");
        assert(addr.port() == 0);
        auto addr_bad = net_address("x!yz");
        assert((*addr_bad).empty());
        assert(!addr_bad);
        std::string enc = url_encode("hello world & test=1");
        std::string dec = url_decode(enc);
        assert(dec == "hello world & test=1");
        std::cout << "utils OK: " << enc << " -> " << dec << std::endl;
    }

    // 4) https client creation (no network, just API existence)
    {
        auto client = https::make_client("https://localhost");
        // client is shared_ptr, check not null; do not actually connect
        assert(client != nullptr);
        std::cout << "https client OK" << std::endl;
    }

    // 5) http header inclusion (ensure httplib symbols available)
    {
        // httplib defines Client; create via web::http namespace
        web::http::Client cli("http://localhost");
        // not connecting, just checking construction
        (void)cli;
        std::cout << "http client OK" << std::endl;
    }

    std::cout << "webforcpp consumer test: OK" << std::endl;
    return 0;
}
