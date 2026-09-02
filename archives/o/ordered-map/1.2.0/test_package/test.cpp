// Consumer-side validation of the packaged tsl headers: exercises the real
// ordered_map / ordered_set APIs and their core guarantee (insertion order
// preserved across insert/erase/rehash). Returns non-zero on any failed check.
#include <cstdint>
#include <cstdio>
#include <string>
#include <utility>

#include <tsl/ordered_map.h>
#include <tsl/ordered_set.h>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    ++g_checks;                                                                \
    if (!(cond)) {                                                             \
      ++g_failed;                                                              \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);              \
    }                                                                          \
  } while (0)

int main() {
  tsl::ordered_map<std::string, int> m;
  m["a"] = 1;
  m["b"] = 2;
  m["c"] = 3;
  CHECK(m.size() == 3 && !m.empty());                              // 1
  CHECK(m.front() == std::make_pair(std::string("a"), 1));         // 2
  CHECK(m.nth(1)->first == "b" && m.nth(1)->second == 2);          // 3 order kept
  CHECK(m.find("c")->second == 3 && m.at("a") == 1);               // 4
  CHECK(m.erase("b") == 1 && m.size() == 2);                       // 5
  CHECK(m.nth(0)->first == "a" && m.nth(1)->first == "c");         // 6 order after erase
  m.rehash(64);
  CHECK(m.nth(0)->first == "a" && m.nth(1)->first == "c");         // 7 order after rehash

  tsl::ordered_set<int> s;
  s.insert(5);
  s.insert(3);
  s.insert(9);
  CHECK(s.size() == 3 && *s.nth(0) == 5 && *s.nth(2) == 9);        // 8 set order
  CHECK(s.erase(3) == 1 && s.count(3) == 0 && s.count(9) == 1);    // 9

  tsl::ordered_map<std::int64_t, std::int64_t> big;
  for (std::int64_t i = 0; i < 1000; ++i) {
    big[i] = i * 10;
  }
  CHECK(big.size() == 1000 && big.nth(500)->second == 5000);       // 10

  std::printf("ordered-map test_package: %d checks, %d failed\n", g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
