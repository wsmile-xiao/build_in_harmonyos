#include <simdjson.h>
#include <iostream>
#include <cassert>

int main(void) {
    simdjson::ondemand::parser parser;
    simdjson::padded_string json(R"({"name":"simdjson","version":395})", 33);
    auto doc = parser.iterate(json);
    std::string_view name = std::string_view(doc.at_pointer("/name"));
    uint64_t version = uint64_t(doc.at_pointer("/version"));
    assert(name == "simdjson");
    assert(version == 395);
    std::cout << "simdjson test passed: name=" << name << " version=" << version << std::endl;
    return 0;
}
