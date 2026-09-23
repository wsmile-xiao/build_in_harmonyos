// test_package for boost1.84-url — 实质测试 Boost.URL API
// （R34：真实调用 boost::urls::url 解析/修改/编码 API，非空壳测试）
#include <boost/url.hpp>
#include <boost/url/encode.hpp>
#include <boost/core/ignore_unused.hpp>
#include <iostream>
#include <string>

int main() {
    int failures = 0;

    // 1. URL 解析（boost::urls::parse_uri + url_view 访问器）
    boost::system::result<boost::urls::url_view> r =
        boost::urls::parse_uri("https://user:pass@www.example.com:8080/path/to/file?query=1&flag#fragment");
    if (!r) {
        std::cerr << "parse_uri failed\n";
        ++failures;
    } else {
        boost::urls::url_view uv = *r;
        if (uv.scheme() != "https") { std::cerr << "scheme mismatch: " << uv.scheme() << "\n"; ++failures; }
        if (uv.host() != "www.example.com") { std::cerr << "host mismatch\n"; ++failures; }
        if (uv.port() != "8080") { std::cerr << "port mismatch\n"; ++failures; }
        if (uv.path() != "/path/to/file") { std::cerr << "path mismatch\n"; ++failures; }
        if (uv.query() != "query=1&flag") { std::cerr << "query mismatch\n"; ++failures; }
        if (uv.fragment() != "fragment") { std::cerr << "fragment mismatch\n"; ++failures; }
    }

    // 2. url 修改操作（可变 URL：set_scheme/set_path/params）
    boost::urls::url u("http://example.com/index.html");
    u.set_scheme(boost::urls::to_string(boost::urls::scheme::https));
    u.set_path("/api/v2");
    u.params().append({{"key", "value"}});
    if (u.buffer() != "https://example.com/api/v2?key=value") {
        std::cerr << "mutation result mismatch: " << u.buffer() << "\n";
        ++failures;
    }

    // 3. 百分号编码/解码
    // unreserved_chars 模式：非保留字符以外的全部编码（含 '/'）
    std::string enc = boost::urls::encode("hello world/你好",
                                          boost::urls::unreserved_chars);
    if (enc != "hello%20world%2F%E4%BD%A0%E5%A5%BD") {
        std::cerr << "encode mismatch: " << enc << "\n";
        ++failures;
    }
    // 解码：url params 视图的 value 自动做百分号解码
    boost::urls::url pu("https://x.com/p?a=hello%20world");
    std::string decoded;
    for (auto param : pu.params()) {
        if (param.key == "a") decoded = param.value;
    }
    if (decoded != "hello world") {
        std::cerr << "pct decode mismatch: " << decoded << "\n";
        ++failures;
    }

    // 4. 相对引用解析（resolve(base, ref, out)）
    boost::urls::url base("https://www.example.com/a/b/c");
    boost::urls::url_view ref = *boost::urls::parse_relative_ref("../d");
    boost::urls::url resolved;
    boost::system::result<void> rv = boost::urls::resolve(base, ref, resolved);
    if (!rv || resolved.buffer() != "https://www.example.com/a/d") {
        std::cerr << "resolve mismatch\n";
        ++failures;
    }

    // 5. segments/params 视图遍历
    boost::urls::url_view sv = *boost::urls::parse_uri("https://x.com/a/b/c");
    int seg_count = 0;
    for (auto seg : sv.segments()) {
        boost::ignore_unused(seg);
        ++seg_count;
    }
    if (seg_count != 3) { std::cerr << "segments count mismatch: " << seg_count << "\n"; ++failures; }

    if (failures == 0) {
        std::cout << "boost1.84-url test_package: ALL PASS (5 groups)\n";
        return 0;
    }
    std::cerr << failures << " failures\n";
    return 1;
}
