// Consumer test for dawgdic: builds a DAWG dictionary through the public
// C++ API, checks exact matching, values, and prefix completion.
#include <cstdio>
#include <string>
#include <vector>

#include <dawgdic/completer.h>
#include <dawgdic/dawg-builder.h>
#include <dawgdic/dawg.h>
#include <dawgdic/dictionary-builder.h>
#include <dawgdic/dictionary.h>
#include <dawgdic/guide-builder.h>
#include <dawgdic/guide.h>

namespace {

int failures = 0;

void check(bool cond, const char *name) {
  std::printf("[%s] %s\n", cond ? "PASS" : "FAIL", name);
  if (!cond) {
    ++failures;
  }
}

}  // namespace

int main() {
  // DawgBuilder requires keys in sorted order.
  const char *keys[] = {"apple", "apricot", "banana", "cherry", "durian"};
  const std::size_t num_keys = sizeof(keys) / sizeof(keys[0]);

  dawgdic::DawgBuilder builder;
  bool inserted = true;
  for (std::size_t i = 0; i < num_keys; ++i) {
    if (!builder.Insert(keys[i], static_cast<dawgdic::ValueType>(i))) {
      inserted = false;
    }
  }
  check(inserted, "DawgBuilder::Insert accepts all sorted keys");
  check(!builder.Insert("apple", 0), "DawgBuilder::Insert rejects duplicate key");

  dawgdic::Dawg dawg;
  check(builder.Finish(&dawg), "DawgBuilder::Finish");

  dawgdic::Dictionary dic;
  check(dawgdic::DictionaryBuilder::Build(dawg, &dic), "DictionaryBuilder::Build");

  bool contains_all = true;
  for (std::size_t i = 0; i < num_keys; ++i) {
    if (!dic.Contains(keys[i])) {
      contains_all = false;
    }
  }
  check(contains_all, "Dictionary::Contains finds all keys");
  check(!dic.Contains("avocado"), "Dictionary::Contains rejects missing key");
  check(!dic.Contains("app"), "Dictionary::Contains rejects strict prefix");

  bool values_ok = true;
  for (std::size_t i = 0; i < num_keys; ++i) {
    dawgdic::ValueType value = -1;
    if (!dic.Find(keys[i], &value) ||
        value != static_cast<dawgdic::ValueType>(i)) {
      values_ok = false;
    }
  }
  check(values_ok, "Dictionary::Find returns per-key values");
  check(dic.Find("avocado") == -1, "Dictionary::Find returns -1 for missing key");

  dawgdic::Guide guide;
  check(dawgdic::GuideBuilder::Build(dawg, dic, &guide),
        "GuideBuilder::Build");

  // Prefix completion for "ap" must yield exactly apple + apricot.
  dawgdic::BaseType index = dic.root();
  bool followed = dic.Follow("ap", &index);
  check(followed, "Dictionary::Follow walks prefix");
  std::vector<std::string> completed;
  if (followed) {
    dawgdic::Completer completer(dic, guide);
    completer.Start(index, "ap");
    while (completer.Next()) {
      completed.push_back(completer.key());
    }
  }
  check(completed.size() == 2 && completed[0] == "apple" &&
        completed[1] == "apricot",
        "Completer enumerates prefix keys");

  if (failures == 0) {
    std::printf("ALL TESTS PASSED\n");
    return 0;
  }
  std::printf("%d TEST(S) FAILED\n", failures);
  return 1;
}
