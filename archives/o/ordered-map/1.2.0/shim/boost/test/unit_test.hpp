// Zero-dependency shim of <boost/test/unit_test.hpp> for HarmonyOS PC CI.
// The ohpcd Conan remote publishes no Boost.Test (unit_test_framework)
// binary, so the upstream ordered-map test bodies are compiled unchanged
// against this minimal harness instead. Semantics kept close to Boost.Test:
//   - BOOST_CHECK*  : non-fatal, case continues, case marked failed
//   - BOOST_REQUIRE*: fatal, aborts the current case (others still run)
//   - BOOST_AUTO_TEST_CASE_TEMPLATE: one runtime case per type in the list
#ifndef SHIM_BOOST_TEST_UNIT_TEST_HPP
#define SHIM_BOOST_TEST_UNIT_TEST_HPP

#include <cassert>
#include <cstdio>
#include <exception>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace shim_boost_test {

struct case_failure : std::exception {
  std::string msg;
  explicit case_failure(std::string m) : msg(std::move(m)) {}
  const char* what() const noexcept override { return msg.c_str(); }
};

inline long& checks() {
  static long n = 0;
  return n;
}

inline int& current_failed() {
  static int n = 0;
  return n;
}

struct CaseEntry {
  std::string name;
  void (*fn)();
};

inline std::vector<CaseEntry>& registry() {
  static std::vector<CaseEntry> r;
  return r;
}

struct Registrar {
  Registrar(const char* name, void (*fn)()) {
    registry().push_back(CaseEntry{name, fn});
  }
};

// Expands a shim type sequence (see <boost/mpl/list.hpp> shim = std::tuple)
// into one registered runtime case per type.
template <typename Seq>
struct expand_seq;

template <typename T, typename... Rest>
struct expand_seq<std::tuple<T, Rest...>> {
  template <template <typename> class Thunk>
  static void reg(const char* base, int i) {
    std::ostringstream os;
    os << base << "<" << i << ">";
    registry().push_back(CaseEntry{os.str(), &Thunk<T>::call});
    expand_seq<std::tuple<Rest...>>::template reg<Thunk>(base, i + 1);
  }
};

template <>
struct expand_seq<std::tuple<>> {
  template <template <typename> class Thunk>
  static void reg(const char*, int) {}
};

inline void report_check(const char* file, int line, const char* expr) {
  ++current_failed();
  std::printf("\n  CHECK failed at %s:%d: %s", file, line, expr);
  std::fflush(stdout);
}

inline int run_all() {
  int total = 0;
  int failed_cases = 0;
  const std::size_t n = registry().size();
  for (std::size_t idx = 0; idx < n; ++idx) {
    const CaseEntry& e = registry()[idx];
    ++total;
    current_failed() = 0;
    std::printf("[%3d/%zu] %s ... ", total, n, e.name.c_str());
    std::fflush(stdout);
    try {
      e.fn();
    } catch (const case_failure& f) {
      ++current_failed();
      std::printf("\n  REQUIRE failed: %s", f.what());
    } catch (const std::exception& ex) {
      ++current_failed();
      std::printf("\n  unexpected exception: %s", ex.what());
    } catch (...) {
      ++current_failed();
      std::printf("\n  unexpected unknown exception");
    }
    if (current_failed() == 0) {
      std::printf("OK\n");
    } else {
      ++failed_cases;
      std::printf("\n  -> case FAILED\n");
    }
  }
  std::printf("ordered-map shim summary: test cases: %d | %d passed | "
              "%d failed | 0 skipped | checks: %ld\n",
              total, total - failed_cases, failed_cases, checks());
  return failed_cases == 0 ? 0 : 1;
}

}  // namespace shim_boost_test

#define BOOST_TEST_MODULE(name)
#define BOOST_AUTO_TEST_SUITE(name)
#define BOOST_AUTO_TEST_SUITE_END()

#define BOOST_AUTO_TEST_CASE(name)                                \
  static void name();                                             \
  static ::shim_boost_test::Registrar reg_##name(#name, &name); \
  static void name()

#define BOOST_AUTO_TEST_CASE_TEMPLATE(name, T, seq)                        \
  template <typename T>                                                    \
  static void name##_tmpl();                                               \
  template <typename T>                                                    \
  struct name##_thunk {                                                    \
    static void call() { name##_tmpl<T>(); }                               \
  };                                                                       \
  struct name##_registrar_t {                                              \
    name##_registrar_t() {                                                 \
      ::shim_boost_test::expand_seq<seq>::template reg<name##_thunk>(      \
          #name, 0);                                                       \
    }                                                                      \
  };                                                                       \
  static name##_registrar_t name##_registrar;                              \
  template <typename T>                                                    \
  static void name##_tmpl()

#define BOOST_CHECK(expr)                                                     \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!(expr)) {                                                            \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #expr);             \
    }                                                                         \
  } while (0)

#define BOOST_CHECK_EQUAL(a, b)                                               \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!((a) == (b))) {                                                      \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #a " == " #b);      \
    }                                                                         \
  } while (0)

#define BOOST_CHECK_NE(a, b)                                                  \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!((a) != (b))) {                                                      \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #a " != " #b);      \
    }                                                                         \
  } while (0)

#define BOOST_CHECK_THROW(stmt, ex)                                           \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    bool shim_caught_ = false;                                                \
    try {                                                                     \
      stmt;                                                                   \
    } catch (const ex&) {                                                     \
      shim_caught_ = true;                                                    \
    } catch (...) {                                                           \
    }                                                                         \
    if (!shim_caught_) {                                                      \
      ::shim_boost_test::report_check(                                        \
          __FILE__, __LINE__, "expected exception " #ex " from " #stmt);      \
    }                                                                         \
  } while (0)

#define BOOST_REQUIRE(expr)                                                   \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!(expr)) {                                                            \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #expr);             \
      throw ::shim_boost_test::case_failure(#expr);                           \
    }                                                                         \
  } while (0)

#define BOOST_REQUIRE_EQUAL(a, b)                                             \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!((a) == (b))) {                                                      \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #a " == " #b);      \
      throw ::shim_boost_test::case_failure(#a " == " #b);                    \
    }                                                                         \
  } while (0)

#define BOOST_REQUIRE_NE(a, b)                                                \
  do {                                                                        \
    ++::shim_boost_test::checks();                                            \
    if (!((a) != (b))) {                                                      \
      ::shim_boost_test::report_check(__FILE__, __LINE__, #a " != " #b);      \
      throw ::shim_boost_test::case_failure(#a " != " #b);                    \
    }                                                                         \
  } while (0)

#define BOOST_ASSERT(expr) assert(expr)

#endif  // SHIM_BOOST_TEST_UNIT_TEST_HPP
