# E2164 - Tolerate Non-Numeric Kernel Release Strings in Version Parsing

## Symptom

A test suite fails en masse with `C++ exception with description "stoi: no
conversion"` thrown from a platform/singleton constructor, even though the
tests themselves never call `std::stoi`.

## Root Cause

Code parses the kernel release string (`uname -r`) by splitting on `.` and
converting the leading tokens with `std::stoi`. On OHOS the release string is
`HongMeng Kernel 1.12.0`, so the first token (`HongMeng Kernel 1`) is not a
valid integer and `std::stoi` throws `std::invalid_argument`. When this happens
inside the constructor of a lazily-initialized singleton (e.g. a `PlatformInfo`
instance created on first use), every caller that touches the singleton — often
large parts of a test suite — dies with the same exception instead of running
its assertions.

## Recommended Fix

1. Wrap the `std::stoi` conversions in `try/catch` for both
   `std::invalid_argument` and `std::out_of_range`.
2. On any parse failure, default the parsed version components to `0` (or a
   documented safe value).
3. Ensure downstream feature detection treats the defaulted version as
   "unknown" and falls back to the safe code paths (e.g. disable
   `copy_file_range` when the major version cannot be trusted).
4. Keep the fallback explicit: a non-numeric release is not an error, it is an
   unknown version.

## Validation

recc 1.4.13 (buildbox 1.4.13) reproduced this on OHOS: 18 CTest cases failed
with `stoi: no conversion` because `PlatformInfo::PlatformInfo()` parsed
`uname -r` = `HongMeng Kernel 1.12.0`. After the tolerant-parse patch, the
`stoi` exceptions disappeared, the affected tests ran their real assertions,
and the suite moved from 77/95 to 81/95 passing (the remaining failures are
independent OHOS platform limitations, not parsing exceptions).

## Scope

Applies to any runtime code or tests that parse kernel version strings,
release strings, or similar version fields where the platform may return a
non-numeric prefix. The fix must not silently accept arbitrary garbage: only
the version-number parse is tolerant; real configuration errors should still
fail loudly.
