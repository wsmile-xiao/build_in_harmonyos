// Consumer test: exercise the installed public C++ API for parsing and writing.
#include <cpp_yyjson.hpp>

#include <iostream>
#include <string>
#include <vector>

int main()
{
    using namespace yyjson;

    auto parsed = read(R"({"id":42,"name":"consumer","values":[3,5,8]})");
    auto object = parsed.as_object();
    if (!object)
    {
        std::cerr << "consumer test: JSON root is not an object\n";
        return 1;
    }

    const auto id = (*object)["id"].as_int();
    const auto name = (*object)["name"].as_string();
    const auto values = (*object)["values"].as_array();
    if (!id || *id != 42 || !name || *name != "consumer" || !values)
    {
        std::cerr << "consumer test: parsed fields differ from input\n";
        return 1;
    }

    const auto numbers = cast<std::vector<int>>(*values);
    if (numbers != std::vector<int>{3, 5, 8})
    {
        std::cerr << "consumer test: array conversion failed\n";
        return 1;
    }

    auto output = writer::object{};
    output.emplace("ok", true);
    output.emplace("count", numbers.size());
    const auto serialized = output.write();
    const auto roundtrip = read(serialized);
    const auto roundtrip_object = roundtrip.as_object();
    if (!roundtrip_object || !(*roundtrip_object)["ok"].as_bool().value_or(false)
        || (*roundtrip_object)["count"].as_uint().value_or(0) != numbers.size())
    {
        std::cerr << "consumer test: writer output did not round-trip\n";
        return 1;
    }

    std::cout << "consumer test: parsed, converted, serialized, and re-parsed JSON\n";
    return 0;
}
