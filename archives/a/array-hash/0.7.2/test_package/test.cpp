#include <iostream>
#include <string>

#include <tsl/array_map.h>
#include <tsl/array_set.h>

namespace {

int check(bool condition, const char* description) {
    if (condition) {
        return 0;
    }
    std::cerr << "FAIL: " << description << '\n';
    return 1;
}

}  // namespace

int main() {
    tsl::array_map<char, int> map;
    map.insert("one", 1);
    map["two"] = 2;

    int failures = 0;
    failures += check(map.size() == 2, "array_map size is 2");
    failures += check(map.at("one") == 1, "array_map at(one) is 1");
    failures += check(map.find("two") != map.end(), "array_map finds two");
    failures += check(map.find("missing") == map.end(),
                      "array_map does not find missing");
    map.erase("one");
    failures += check(map.count("one") == 0, "array_map erased one");

    tsl::array_set<char> set;
    set.insert("alpha");
    set.insert("beta");
    failures += check(set.size() == 2, "array_set size is 2");
    failures += check(set.count("alpha") == 1, "array_set finds alpha");
    failures += check(set.erase("beta") == 1, "array_set erases beta");
    failures += check(set.count("beta") == 0, "array_set erased beta");

    if (failures != 0) {
        std::cerr << "array-hash consumer test FAILED (" << failures
                  << " check(s))\n";
        return 1;
    }
    std::cout << "array-hash consumer test PASSED\n";
    return 0;
}
