// Consumer smoke test for cxxtools 3.0.0 — exercises real public APIs.
// 8 checks: base64 x2, md5 x2, convert x2, net::Uri x2.
#include <iostream>
#include <sstream>
#include <string>

#include <cxxtools/base64codec.h>
#include <cxxtools/base64stream.h>
#include <cxxtools/md5.h>
#include <cxxtools/md5stream.h>
#include <cxxtools/convert.h>
#include <cxxtools/net/uri.h>

static int g_checks = 0;
static int g_passed = 0;
static int g_failed = 0;

// Non-short-circuiting check: record failure and continue so the preflight
// log shows every check outcome (a short-circuit return hides checks 5-8
// when check 4 fails). On failure the actual value is printed for triage.
#define CHECK(cond, msg) \
    do { \
        ++g_checks; \
        if (!(cond)) { \
            ++g_failed; \
            std::cerr << "FAIL: " << msg << std::endl; \
        } else { \
            ++g_passed; \
            std::cout << "PASS: " << msg << std::endl; \
        } \
    } while (0)

int main()
{
    try
    {
        // 1-2: base64 encode/decode round-trip (mirrors test/base64-test.cpp)
        std::string b64;
        try { b64 = cxxtools::encode<cxxtools::Base64Codec>("123456789"); }
        catch (const std::exception& e) { b64 = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: base64 encode actual=[" << b64 << "]" << std::endl;
        CHECK(b64 == "MTIzNDU2Nzg5", "base64 encode 123456789");
        std::string raw;
        try { raw = cxxtools::decode<cxxtools::Base64Codec>(b64); }
        catch (const std::exception& e) { raw = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: base64 decode actual=[" << raw << "]" << std::endl;
        CHECK(raw == "123456789", "base64 decode round-trip");

        // 3-4: md5 digests (mirrors test/md5-test.cpp vectors)
        std::string md5empty;
        try { md5empty = cxxtools::md5(""); }
        catch (const std::exception& e) { md5empty = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: md5(\"\") actual=[" << md5empty << "]" << std::endl;
        CHECK(md5empty == "d41d8cd98f00b204e9800998ecf8427e", "md5 empty string");
        std::string fox;
        try
        {
            cxxtools::Md5stream md5;
            md5 << "The quick brown fox jumps over the lazy dog.";
            fox = md5.getHexDigest();
        }
        catch (const std::exception& e) { fox = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: Md5stream fox actual=[" << fox << "]" << std::endl;
        CHECK(fox == "e4d909c290d0fb1ca068ffaddf22cbd0", "Md5stream fox digest");

        // 5-6: string conversion (mirrors test/convert-test.cpp)
        std::string convN;
        int n = 0;
        try
        {
            n = cxxtools::convert<int>(std::string(" -15 "));
            convN = cxxtools::convert<std::string>(n);
        }
        catch (const std::exception& e) { convN = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: convert<int>(\" -15 \") actual=[" << n << "] as-string=[" << convN << "]" << std::endl;
        CHECK(n == -15, "convert<int> with whitespace");
        std::string s;
        try { s = cxxtools::convert<std::string>(42); }
        catch (const std::exception& e) { s = std::string("EXCEPTION: ") + e.what(); }
        std::cout << "INFO: convert<string>(42) actual=[" << s << "]" << std::endl;
        CHECK(s == "42", "convert<string> from int");

        // 7-8: URI parsing (mirrors test/uri-test.cpp, header cxxtools/net/uri.h)
        std::string host, path;
        try
        {
            cxxtools::net::Uri uri("http://www.tntnet.org/index.html");
            host = uri.host();
            path = uri.path();
        }
        catch (const std::exception& e)
        {
            host = std::string("EXCEPTION: ") + e.what();
            path = host;
        }
        std::cout << "INFO: uri host actual=[" << host << "] path actual=[" << path << "]" << std::endl;
        CHECK(host == "www.tntnet.org", "uri host");
        CHECK(path == "/index.html", "uri path");
    }
    catch (const std::exception& e)
    {
        std::cerr << "FAIL: uncaught std::exception: " << e.what() << std::endl;
        ++g_failed;
    }
    catch (...)
    {
        std::cerr << "FAIL: uncaught unknown exception" << std::endl;
        ++g_failed;
    }

    std::cout << "Results: " << g_passed << "/" << g_checks << " checks passed";
    if (g_failed)
        std::cout << " (" << g_failed << " failed)";
    std::cout << std::endl;
    return (g_failed == 0 && g_checks == 8) ? 0 : 1;
}
