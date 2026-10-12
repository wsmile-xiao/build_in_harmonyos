// Consumer test for libcuckoo-acp — 10 real API checks on cuckoohash_map.
// Each check prints "LIBCUCKOO_ACP_CHECK <n> <name> PASS|FAIL"; the final
// "LIBCUCKOO_ACP_TEST total=10 passed=N" summary line is the single counting
// source for the HMBS_TEST_PACKAGE_RESULT marker. Exit code is 0 if and only
// if all 10 checks pass, so the harness cannot mistake silence for success.
#include <libcuckoo/cuckoohash_map.hh>

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

int g_passed = 0;
int g_total = 0;

void check(int n, const char *name, bool cond) {
    ++g_total;
    if (cond) {
        ++g_passed;
        std::cout << "LIBCUCKOO_ACP_CHECK " << n << " " << name << " PASS" << std::endl;
    } else {
        std::cout << "LIBCUCKOO_ACP_CHECK " << n << " " << name << " FAIL" << std::endl;
    }
}

} // namespace

int main() {
    libcuckoo::cuckoohash_map<int, std::string> map;

    // 1: insert three key-value pairs.
    bool ins = map.insert(1, "hello") && map.insert(2, "world") && map.insert(3, "libcuckoo");
    check(1, "insert", ins);

    // 2: find returns the inserted values.
    std::string val;
    bool found = map.find(1, val) && val == "hello" && map.find(2, val) && val == "world" &&
                 map.find(3, val) && val == "libcuckoo";
    check(2, "find", found);

    // 3: missing key is not found.
    check(3, "find-missing", !map.find(99, val));

    // 4: size reports the inserted count.
    check(4, "size", map.size() == 3);

    // 5: erase removes the key and shrinks the table.
    map.erase(2);
    check(5, "erase", !map.find(2, val) && map.size() == 2);

    // 6: update overwrites the mapped value.
    map.update(1, "updated");
    check(6, "update", map.find(1, val) && val == "updated");

    // 7: upsert inserts a new key and updates an existing one.
    auto adder = [](std::string &v) { v += "!"; };
    map.upsert(4, adder, "fresh");
    map.upsert(1, adder, "unused");
    check(7, "upsert", map.find(4, val) && val == "fresh" && map.find(1, val) &&
                            val == "updated!");

    // 8: locked_table view sees the same live entries.
    // NOTE: locked_table::find(key) takes a single key and returns an
    // iterator (no bool+out-param overload unlike the concurrent map),
    // so compare via iterator dereference.
    {
        auto locked = map.lock_table();
        auto it = locked.find(3);
        check(8, "locked-table", locked.size() == 3 && it != locked.end() &&
                                      it->second == "libcuckoo");
    }

    // 9: clear empties the table.
    map.clear();
    check(9, "clear-empty", map.empty() && map.size() == 0);

    // 10: throwing find on a missing key raises std::out_of_range.
    bool threw = false;
    try {
        map.find(12345);
    } catch (const std::out_of_range &) {
        threw = true;
    }
    check(10, "find-throws", threw);

    std::cout << "LIBCUCKOO_ACP_TEST total=" << g_total << " passed=" << g_passed << std::endl;
    return (g_passed == 10 && g_total == 10) ? 0 : 1;
}
