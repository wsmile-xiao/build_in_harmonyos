#include <unordered_map.hpp>

#include <iostream>
#include <string>
#include <utility>

int main() {
    int discovered = 0;
    int passed = 0;
#define CHECK(condition) do { ++discovered; if (condition) { ++passed; } else { std::cerr << "failed: " #condition << '\n'; } } while (false)

    ska::unordered_map<std::string, int> values;
    CHECK(values.empty());
    CHECK(values.emplace("red", 3).second);
    values["blue"] = 7;
    CHECK(values.size() == 2);
    CHECK(values.at("red") == 3);
    CHECK(values.find("blue") != values.end() && values.find("blue")->second == 7);
    CHECK(values.erase("red") == 1 && values.count("red") == 0);

    ska::unordered_map<std::string, int> moved(std::move(values));
    CHECK(moved.size() == 1 && moved.at("blue") == 7);

    ska::unordered_set<int> set = {10, 20, 30};
    CHECK(!set.insert(20).second && set.insert(40).second);
    CHECK(set.count(10) == 1 && set.erase(10) == 1 && set.count(10) == 0);

    const bool ok = discovered == 9 && passed == discovered;
    std::cout << "unordered_map: " << passed << '/' << discovered << " passed\n";
    return ok ? 0 : 1;
}
