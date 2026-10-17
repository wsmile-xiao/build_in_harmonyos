#include <cassert>
#include <string>

#include <cxxopts.hpp>

int main()
{
    cxxopts::Options options("consumer");
    options.add_options()
        ("v,verbose", "enable verbose output")
        ("n,name", "user name", cxxopts::value<std::string>());

    const char* argv[] = {
        "consumer", "--verbose", "--name", "Harmony"
    };
    const auto result = options.parse(4, argv);

    assert(result.count("verbose") == 1);
    assert(result["name"].as<std::string>() == "Harmony");
    assert(options.help().find("verbose") != std::string::npos);
}
