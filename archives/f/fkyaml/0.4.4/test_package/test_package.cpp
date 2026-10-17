// test_package.cpp — real fkYAML API consumption test (R34 anti-shell).
// Parses YAML, reads values, order-preserving iteration, serializes back.
// Note: <ios> (for std::streamsize) must precede fkYAML headers — upstream
// str_view.hpp uses std::streamsize without including <ios> itself.
#include <ios>

#include <fkYAML/node.hpp>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    // Basic deserialization of a nested mapping.
    fkyaml::node root = fkyaml::node::deserialize(
        "name: test_package\nversion: 0.4.4\nfeatures:\n  - yaml\n  - header_only\n");

    assert(root["name"].get_value<std::string>() == "test_package");
    assert(root["version"].get_value<std::string>() == "0.4.4");
    assert(root["features"].is_sequence());
    assert(root["features"].size() == 2);
    assert(root["features"][0].get_value<std::string>() == "yaml");
    assert(root["features"][1].get_value<std::string>() == "header_only");

    // Order-preserving mapping: insertion order must be kept.
    fkyaml::node ordered = fkyaml::node::mapping();
    ordered["z"] = 1;
    ordered["a"] = 2;
    ordered["m"] = 3;
    std::string keys;
    for (const auto& entry : ordered.map_items()) {
        keys += entry.key().get_value<std::string>();
    }
    assert(keys == "zam"); // insertion order preserved, not sorted

    // Integer / float round trip through serialization.
    fkyaml::node num(42);
    std::string dumped = fkyaml::node::serialize(num);
    assert(dumped.find("42") != std::string::npos);

    // Exception path: deserializing invalid YAML must throw.
    bool threw = false;
    try {
        (void)fkyaml::node::deserialize("a: [unclosed");
    } catch (const fkyaml::parse_error&) {
        threw = true;
    }
    assert(threw);

    std::cout << "test_package: fkYAML API consumption OK" << std::endl;
    return 0;
}