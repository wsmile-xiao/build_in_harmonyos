// Consumer smoke test for libmcfp 2.1.1 — drives the real parsing API on device.
// Uses only the installed public header mcfp/mcfp.hpp and the public library
// target (libmcfp::libmcfp), like a third-party downstream component would.
#include <mcfp/mcfp.hpp>

#include <iostream>
#include <string>
#include <system_error>
#include <vector>

int main()
{
    auto &config = mcfp::config::instance();

    config.init("usage: test_libmcfp [options]",
                mcfp::make_option<int>("num,n", 1, "a number"),
                mcfp::make_option<std::string>("text,t", "x", "some text"),
                mcfp::make_option<std::vector<std::string>>("item,i",
                                                            "repeatable item"));

    const char *const args[] = {"test_libmcfp", "-n", "7", "--text", "hello",
                                "-i", "a", "-i", "b"};
    std::error_code ec;
    config.parse(9, args, ec);
    if (ec) {
        std::cerr << "mcfp parse error: " << ec.message() << "\n";
        return 1;
    }

    const int n = config.get<int>("num");
    const std::string t = config.get<std::string>("text");
    const auto items = config.get<std::vector<std::string>>("item");

    if (n != 7 || t != "hello" || items.size() != 2 ||
        items[0] != "a" || items[1] != "b") {
        std::cerr << "mcfp consumer bad values: num=" << n << " text=" << t
                  << " items=" << items.size() << "\n";
        return 2;
    }

    std::cout << "mcfp consumer smoke OK (num=" << n << ", text=" << t
              << ", items=" << items.size() << ")\n";
    return 0;
}
