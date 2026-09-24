// Consumer-side validation for the packaged re-flex library: the matcher
// API (find / matches / text) must behave as documented when linked against
// the packaged libreflex.a.  Exit 0 + "CONSUMER_OK" = pass; any failure
// exits 1 with a CONSUMER_FAIL line.
#include <reflex/matcher.h>
#include <reflex/pattern.h>

#include <cstdio>
#include <cstring>
#include <string>

int main()
{
  // NB: reflex::Matcher stores a reference to its Pattern - the Pattern must
  // be a named object (a temporary dangles past the constructor line, and
  // every match then reports 0).  This mirrors upstream tests/rtest.cpp,
  // which always binds a named Pattern before constructing a Matcher.

  // 1) find(): tokenize "How now brown cow." into 4 words, last one "cow".
  reflex::Pattern word_pattern("\\w+");
  reflex::Matcher matcher(word_pattern, "How now brown cow.");
  int words = 0;
  std::string last;
  while (matcher.find() != 0) {
    last = matcher.text();
    ++words;
  }
  if (words != 4 || last != "cow") {
    std::printf("CONSUMER_FAIL find words=%d last=%s\n", words, last.c_str());
    return 1;
  }

  // 2) matches(): full-string match with capture groups.
  reflex::Pattern pair_pattern("([0-9]+)-([a-z]+)");
  reflex::Matcher m2(pair_pattern, "123-abc");
  if (m2.matches() == 0 || std::strcmp(m2.text(), "123-abc") != 0) {
    std::printf("CONSUMER_FAIL matches\n");
    return 1;
  }

  std::printf("CONSUMER_OK words=%d text=%s\n", words, m2.text());
  return 0;
}
