#include <toml.hpp>
#include <iostream>
#include <sstream>
#include <cassert>
#include <vector>

int main() {
    // Test: parse a TOML string and access values
    std::istringstream iss(R"(
title = "toml11 test"

[database]
server = "192.168.1.1"
ports = [8001, 8002, 8003]
connection_max = 5000

[owner]
name = "Tom Preston-Werner"
)");
    auto data = toml::parse(iss);

    // Verify string value
    std::string title = toml::find<std::string>(data, "title");
    assert(title == "toml11 test");

    // Verify nested table access using multi-key find
    std::string server = toml::find<std::string>(data, "database", "server");
    assert(server == "192.168.1.1");

    // Verify integer value
    int connection_max = toml::find<int>(data, "database", "connection_max");
    assert(connection_max == 5000);

    // Verify owner name
    std::string owner = toml::find<std::string>(data, "owner", "name");
    assert(owner == "Tom Preston-Werner");

    // Verify array access via vector
    std::vector<int> ports = toml::find<std::vector<int>>(data, "database", "ports");
    assert(ports.size() == 3);
    assert(ports[0] == 8001);
    assert(ports[1] == 8002);
    assert(ports[2] == 8003);

    // Verify array element access via index
    assert(toml::find<int>(data, "database", "ports", 0) == 8001);
    assert(toml::find<int>(data, "database", "ports", 1) == 8002);

    std::cout << "All toml11 tests passed!" << std::endl;
    return 0;
}
