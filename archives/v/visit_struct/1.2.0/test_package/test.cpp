/* test_package for visit_struct 1.2.0 — exercises the real reflection API.
 * Returns non-zero if any CHECK fails. */
#include <visit_struct/visit_struct.hpp>

#include <cstdio>
#include <string>
#include <utility>
#include <vector>

struct point_t {
  int x;
  float y;
  std::string label;
};
VISITABLE_STRUCT(point_t, x, y, label);

/* Registered in non-declaration order on purpose: visitation must follow
 * the registration order (b before a). */
struct pair_t {
  double a;
  bool b;
};
VISITABLE_STRUCT(pair_t, b, a);

struct plain_t {
  int z;
};

static int checks = 0;
static int failures = 0;
#define CHECK(cond)                                                          \
  do {                                                                       \
    ++checks;                                                                \
    if (!(cond)) {                                                           \
      ++failures;                                                            \
      std::printf("FAIL: %s\n", #cond);                                      \
    }                                                                        \
  } while (0)

struct collector {
  std::vector<std::pair<std::string, std::string>> kv;

  template <typename T>
  void operator()(const char * name, const T & value) {
    kv.emplace_back(std::string{name}, std::to_string(value));
  }

  void operator()(const char * name, const std::string & value) {
    kv.emplace_back(std::string{name}, value);
  }
};

int main() {
  CHECK(visit_struct::traits::is_visitable<point_t>::value);
  CHECK(!visit_struct::traits::is_visitable<plain_t>::value);
  CHECK(visit_struct::field_count<point_t>() == 3);
  CHECK(visit_struct::field_count<pair_t>() == 2);

  point_t p{7, 2.5f, "ohos"};
  collector c;
  visit_struct::for_each(p, c);
  CHECK(c.kv.size() == 3);
  CHECK(c.kv[0].first == "x" && c.kv[0].second == "7");
  CHECK(c.kv[1].first == "y");
  CHECK(c.kv[2].first == "label" && c.kv[2].second == "ohos");

  CHECK(std::string(visit_struct::get_name<0>(p)) == "x");

  pair_t q{0.5, true};
  collector c2;
  visit_struct::for_each(q, c2);
  CHECK(c2.kv.size() == 2 && c2.kv[0].first == "b" && c2.kv[1].first == "a");

  std::printf("visit_struct test_package: %d checks, %d failed\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
