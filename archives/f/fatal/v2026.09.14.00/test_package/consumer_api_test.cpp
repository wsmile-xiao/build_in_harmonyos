/*
 * fatal v2026.09.14.00 — consumer test (HarmonyOS PC / aarch64).
 *
 * Real consumer surface: `#include <fatal/...>` only through the installed
 * package include dir, type-level assertions plus a runtime traversal of a
 * fatal::list via fatal::foreach (not a pure-assertion test).
 */
#include <fatal/type/foreach.h>
#include <fatal/type/list.h>
#include <fatal/type/push.h>
#include <fatal/type/reverse.h>
#include <fatal/type/size.h>

#include <cstdio>
#include <string>
#include <type_traits>
#include <typeinfo>
#include <vector>

namespace {

struct foo { static const char *name() { return "foo"; } };
struct bar { static const char *name() { return "bar"; } };
struct baz { static const char *name() { return "baz"; } };

struct collect_visitor {
  template <typename Type, std::size_t Index>
  void operator()(fatal::indexed<Type, Index>,
                  std::vector<std::string> &out) const {
    out.push_back(std::string(Type::name()) + "@" + std::to_string(Index));
  }
};

} // namespace

int main() {
  // ── type level: list / size / reverse / push_front ──
  using base = fatal::list<int, double, char>;
  using reversed = fatal::reverse<base>;
  using pushed = fatal::push_front<base, void *>;

  static_assert(fatal::size<base>::value == 3, "fatal::size<list<int,double,char>>");
  static_assert(fatal::size<fatal::list<>>::value == 0, "fatal::size<list<>>");
  static_assert(std::is_same<reversed, fatal::list<char, double, int>>::value,
                "fatal::reverse<list<int,double,char>>");
  static_assert(std::is_same<pushed,
                             fatal::list<void *, int, double, char>>::value,
                "fatal::push_front<list<int,double,char>, void *>");

  // ── runtime: traverse a fatal::list with fatal::foreach ──
  std::vector<std::string> seen;
  fatal::foreach<fatal::list<foo, bar, baz>>(collect_visitor(), seen);

  const std::vector<std::string> expected{"foo@0", "bar@1", "baz@2"};
  if (seen != expected) {
    std::printf("FAIL: fatal::foreach produced");
    for (const auto &item : seen) {
      std::printf(" %s", item.c_str());
    }
    std::printf("\n");
    return 1;
  }

  std::printf("fatal v2026.09.14.00 consumer API OK: size=3, reverse/push_front "
              "verified, foreach visited %zu types (%s)\n",
              seen.size(), seen.back().c_str());
  return 0;
}
