# clue

clue is a tiny header-only C++ logging framework by Martin Moene: log
messages with a severity and an optional module identifier. Logging
destinations provided by the single header: console (default), text file,
in-memory string log; Windows debugger/event log and Unix syslog are only
compiled in when explicitly requested via `clue_LOG_TO_*` macros.

- Homepage: https://github.com/martinmoene/clue
- License: Boost Software License 1.0 (`LICENSE_1_0.txt`)

## HarmonyOS PC adaptation notes

- The upstream ships no build system for the library itself (it is a single
  header) — only `tests/Makefile` for the lest test suite, which the recipe
  reuses to compile AND run the real upstream tests during `build()`.
- Consumers must `using namespace clue;` (or define
  `clue_LOG_TO_STRING`/custom expression macros) because the short-name
  `LOG_*` macros expand to an unqualified `the_log()` reference.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.0.0   | built  | HarmonyOS PC (aarch64) Conan adaptation |
