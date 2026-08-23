#include <toml++/toml.h>
#include <cassert>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    // Test parsing a TOML string
    auto tbl = toml::parse(R"(
        name = "OpenHarmony"
        version = "3.4.0"
        [dependencies]
        zlib = "1.3.1"
    )");

    // Verify parsed values
    assert(tbl["name"].value<std::string>() == "OpenHarmony");
    assert(tbl["version"].value<std::string>() == "3.4.0");

    auto deps = tbl["dependencies"].as_table();
    assert(deps != nullptr);
    assert(deps->get("zlib")->value<std::string>() == "1.3.1");

    // Test serialization
    std::ostringstream oss;
    oss << toml::default_formatter{tbl};
    std::string output = oss.str();
    assert(output.find("OpenHarmony") != std::string::npos);

    // Test table construction and serialization
    auto new_tbl = toml::table{
        {"title", "Test Suite"},
        {"passed", true},
    };
    std::ostringstream oss2;
    oss2 << toml::default_formatter{new_tbl};
    std::string serialized = oss2.str();
    assert(serialized.find("Test Suite") != std::string::npos);

    std::cout << "All tests passed!\n";
    return 0;
}
