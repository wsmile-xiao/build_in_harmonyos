# Boost.Regex 1.84.0 HarmonyOS adaptation

Boost.Build is not used because its shell probes are incompatible with the
HarmonyOS target. The recipe compiles the five upstream Boost.Regex source
files directly and packages `libboost_regex.a`.

The consumer test exercises regular-expression matching, capture groups and
replacement on the target device.

The full upstream test sweep (all 52 source files under libs/regex/test:
50 C++ files and 2 C compiler-check files) was executed on OHOS armv8
following upstream Jamfile.v2 semantics:

- regress suite: main.cpp + 21 TUs built as one binary, EXIT=0.
- 15 run targets compiled, linked and executed, all EXIT=0
  (captures_test with BOOST_REGEX_MATCH_EXTRA; unicode_iterator_test in
  both TEST_UTF8 and TEST_UTF16 variants).
- 3 concepts targets (link semantics) linked successfully.
- 9 compile-only targets passed compilation, including test_consolidated
  and test_warnings with -Wall -Werror.
- static_mutex_test needed a pthread_setcancelstate declaration shim
  (musl lacks the prototype though the symbol exists) and
  BOOST_TIMER_ENABLE_DEPRECATED.

Result: 51 passed, 1 skipped, 0 failed. The single skip is quick_icu.cpp,
which requires ICU headers (unicode/coll.h) that are unavailable on OHOS;
this is an environment limitation, not a library defect.
