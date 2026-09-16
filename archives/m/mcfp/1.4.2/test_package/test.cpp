// Consumer smoke test for mcfp 1.4.2 — drives the real parsing API on device.
#include <mcfp/mcfp.hpp>

#include <iostream>
#include <string>
#include <system_error>

int main()
{
    auto &config = mcfp::config::instance();

    config.init("usage: test_mcfp [options]",
                mcfp::make_option<int>("num,n", 1, "a number"),
                mcfp::make_option<std::string>("text,t", "x", "some text"));

    const char *const args[] = {"test_mcfp", "-n", "7", "--text", "hello"};
    std::error_code ec;
    config.parse(5, args, ec);
    if (ec) {
        std::cerr << "mcfp parse error: " << ec.message() << "\n";
        return 1;
    }

    const int n = config.get<int>("num");
    const std::string t = config.get<std::string>("text");

    if (n != 7 || t != "hello") {
        std::cerr << "mcfp consumer bad values: num=" << n << " text=" << t << "\n";
        return 2;
    }

    std::cout << "mcfp consumer smoke OK (num=" << n << ", text=" << t << ")\n";
    return 0;
}
