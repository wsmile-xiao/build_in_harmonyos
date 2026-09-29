/*
 * fatal v2026.09.14.00 — HarmonyOS-specific test #3: public header surface under the
 * OHOS libc++ toolchain.
 *
 * The OHOS native toolchain (clang 15 + libcxx-ohos) is stricter than the
 * toolchains upstream fatal is developed against: `-Werror -Wextra` plus
 * hardened standard headers.  This TU pulls in the public, non-deprecated
 * `fatal/type/` surface and evaluates it, so any new -Werror breakage in a
 * header (the rope.h std::iterator class of problem) fails loudly.
 *
 * It also exercises the std::tuple_element hardening that the upstream
 * suite tripped over (see patch 0002): in-range indices are complete types
 * and must still be probed successfully by fatal::is_complete.
 */
#include <fatal/type/apply.h>
#include <fatal/type/arithmetic.h>
#include <fatal/type/conditional.h>
#include <fatal/type/constant.h>
#include <fatal/type/fast_pass.h>
#include <fatal/type/fold.h>
#include <fatal/type/foreach.h>
#include <fatal/type/has_type.h>
#include <fatal/type/identity.h>
#include <fatal/type/is_complete.h>
#include <fatal/type/list.h>
#include <fatal/type/pair.h>
#include <fatal/type/push.h>
#include <fatal/type/sequence.h>
#include <fatal/type/size.h>
#include <fatal/type/tag.h>
#include <fatal/type/traits.h>

#include <cstdio>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

int main() {
  using pair = std::pair<void, void>;

  // in-range tuple elements are complete types under the hardened libc++
  static_assert(fatal::is_complete<std::tuple_element<0, pair>>::value,
                "tuple_element<0, pair> is complete");
  static_assert(fatal::is_complete<std::tuple_element<1, pair>>::value,
                "tuple_element<1, pair> is complete");
  static_assert(fatal::is_complete<int>::value, "int is complete");
  static_assert(!fatal::is_complete<void>::value ||
                    fatal::is_complete<void>::value,
                "is_complete<void> must at least compile");

  // fatal's own type machinery on top of the OHOS standard library
  using seq = fatal::index_sequence<0, 1, 2>;
  static_assert(fatal::size<seq>::value == 3, "fatal::size<index_sequence>");
  static_assert(std::is_same<fatal::identity<int>, int>::value,
                "fatal::identity");

  const std::string label = "OHOS libc++ surface";
  std::printf("fatal v2026.09.14.00 %s OK: fatal/type/ public headers compile under "
              "-Wall -Werror -Wextra -std=c++17; tuple_element hardening "
              "handled (%s)\n",
              label.c_str(), std::to_string(fatal::size<seq>::value).c_str());
  return 0;
}
