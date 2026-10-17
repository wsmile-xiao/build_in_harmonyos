// test_libmcfp.cpp — Substantive test for libmcfp header-only library
// Exercises mcfp's command-line parsing API (R34: must call real API)

#include <mcfp/mcfp.hpp>
#include <iostream>
#include <cstdlib>

int main(int argc, char * const argv[])
{
    auto &config = mcfp::config::instance();

    config.init(
        "usage: test_libmcfp [options]",
        mcfp::make_option("help,h", "Print help text"),
        mcfp::make_option("verbose,v", "Verbose mode"),
        mcfp::make_option<std::string>("name", "Default", "A name parameter"),
        mcfp::make_option<int>("count", 1, "A count parameter")
    );

    std::error_code ec;
    config.parse(argc, argv, ec);
    if (ec)
    {
        std::cerr << "Error: " << ec.message() << std::endl;
        return 1;
    }

    // Exercise the API: check for help flag
    if (config.has("help"))
    {
        std::cout << config << std::endl;
        return 0;
    }

    // Exercise the API: get option values
    int count = config.get<int>("count");
    std::string name = config.get<std::string>("name");

    std::cout << "name=" << name << " count=" << count << std::endl;

    // Exercise the API: check verbose count
    int verbose_count = config.count("verbose");
    std::cout << "verbose=" << verbose_count << std::endl;

    // Exercise the API: check operands
    auto ops = config.operands();
    std::cout << "operands=" << ops.size() << std::endl;

    return 0;
}
