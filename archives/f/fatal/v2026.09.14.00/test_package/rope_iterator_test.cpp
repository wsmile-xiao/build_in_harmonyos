/*
 * fatal v2026.09.14.00 — HarmonyOS-specific test #2: rope const_iterator.
 *
 * Guards patch 0001 (fatal/string/rope.h no longer derives its
 * const_iterator from the C++17-deprecated std::iterator).  Compiles under
 * -Wall -Werror -Wextra and checks at runtime that the iterator still walks
 * the rope correctly, plus at compile time that the typedefs it used to
 * inherit are still exposed (they are part of the public iterator
 * contract consumed by <algorithm>/std::iterator_traits).
 */
#include <fatal/string/rope.h>

#include <cstdio>
#include <iterator>
#include <string>
#include <type_traits>

int main() {
  fatal::rope<> r(std::string("hello"), ", ", std::string("world"), '!');
  const std::string expected("hello, world!");

  const std::string flat = r.to_string();
  if (flat != expected) {
    std::printf("FAIL: rope::to_string() = '%s'\n", flat.c_str());
    return 1;
  }

  // runtime traversal through the patched const_iterator
  std::string walked;
  std::size_t count = 0;
  for (auto const ch : r) {
    walked.push_back(ch);
    ++count;
  }
  if (walked != expected || count != expected.size()) {
    std::printf("FAIL: const_iterator walk = '%s' (%zu chars)\n",
                walked.c_str(), count);
    return 1;
  }

  // the typedefs std::iterator<bidirectional_iterator_tag, char, ptrdiff_t>
  // used to supply must remain available on the patched iterator
  using it = fatal::rope<>::const_iterator;
  static_assert(std::is_same<it::iterator_category,
                             std::bidirectional_iterator_tag>::value,
                "const_iterator::iterator_category");
  static_assert(std::is_same<it::value_type, char>::value,
                "const_iterator::value_type");
  static_assert(std::is_same<it::difference_type, std::ptrdiff_t>::value,
                "const_iterator::difference_type");
  static_assert(std::is_same<it::pointer, char *>::value,
                "const_iterator::pointer");
  static_assert(std::is_same<it::reference, char &>::value,
                "const_iterator::reference");
  static_assert(std::is_same<
                  std::iterator_traits<it>::iterator_category,
                  std::bidirectional_iterator_tag>::value,
                "std::iterator_traits<const_iterator>");

  std::printf("fatal v2026.09.14.00 rope const_iterator OK: walked '%s' "
              "(%zu chars, std::distance=%td)\n",
              walked.c_str(), count, std::distance(r.begin(), r.end()));
  return 0;
}
