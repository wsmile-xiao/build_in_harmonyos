#include <flat_hash_map.hpp>

#include <iostream>
#include <string>
#include <utility>

int main() {
    int discovered = 0;
    int passed = 0;
#define CHECK(condition) do { ++discovered; if (condition) { ++passed; } else { std::cerr << "failed: " #condition << '\n'; } } while (false)

    ska::flat_hash_map<std::string, int> values;
    values.reserve(32);
    CHECK(values.empty());
    CHECK(values.emplace("one", 1).second);
    values["two"] = 2;
    CHECK(values.size() == 2);
    CHECK(values.find("one") != values.end() && values.find("one")->second == 1);
    CHECK(values.count("missing") == 0);
    CHECK(values.erase("one") == 1 && values.count("one") == 0);

    ska::flat_hash_map<std::string, int> copy(values);
    CHECK(copy == values);
    ska::flat_hash_map<std::string, int> moved(std::move(copy));
    CHECK(moved.at("two") == 2);

    ska::flat_hash_set<int> set = {1, 2, 3};
    CHECK(!set.insert(2).second && set.insert(4).second);
    CHECK(set.size() == 4 && set.count(4) == 1);

    const bool ok = discovered == 10 && passed == discovered;
    std::cout << "flat_hash_map: " << passed << '/' << discovered << " passed\n";
    return ok ? 0 : 1;
}
