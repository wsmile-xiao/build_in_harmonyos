#include <bytell_hash_map.hpp>

#include <iostream>
#include <string>
#include <utility>

int main() {
    int discovered = 0;
    int passed = 0;
#define CHECK(condition) do { ++discovered; if (condition) { ++passed; } else { std::cerr << "failed: " #condition << '\n'; } } while (false)

    ska::bytell_hash_map<std::string, int> values;
    CHECK(values.empty());
    CHECK(values.emplace("alpha", 11).second);
    values["beta"] = 22;
    CHECK(values.size() == 2);
    CHECK(values.at("alpha") == 11);
    CHECK(values.find("beta") != values.end() && values.find("beta")->second == 22);
    CHECK(values.erase("alpha") == 1 && values.count("alpha") == 0);

    ska::bytell_hash_map<std::string, int> copy(values);
    CHECK(copy == values);
    ska::bytell_hash_map<std::string, int> moved(std::move(copy));
    CHECK(moved.count("beta") == 1);

    ska::bytell_hash_set<int> set = {5, 6, 7};
    CHECK(!set.insert(6).second && set.insert(8).second);
    CHECK(set.erase(5) == 1 && set.size() == 3);

    const bool ok = discovered == 10 && passed == discovered;
    std::cout << "bytell_hash_map: " << passed << '/' << discovered << " passed\n";
    return ok ? 0 : 1;
}
