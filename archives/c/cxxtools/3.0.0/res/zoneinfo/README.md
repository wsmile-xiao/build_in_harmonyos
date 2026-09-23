# Timezone test fixtures (generated at test time, never committed)

The cxxtools 3.0.0 `tz` unit suite (`test/tz-test.cpp`) needs three IANA
timezone files: `Europe/Berlin`, `Pacific/Samoa`, `UTC`. The suite reads
them through `$TZDIR/<name>` (default `/usr/share/zoneinfo`, absent on
HarmonyOS). The recipe (`conanfile.py::_prepare_zoneinfo`) runs
`generate_berlin_fat.py --all <tmpdir>/tzdata_generated` before
`test/alltests -s` and points `TZDIR` there with `TZ=UTC`; the files live
only on the test machine, they are exported for the build but never
packaged into the library.

No binaries are committed in this directory on purpose: CI restores the PR
via `curl .../pull.diff + git apply`, which cannot carry GIT binary
patches (`missing binary patch data`), so any vendored binary breaks
checkout. Everything here is UTF-8 text.

## Provenance

- `Pacific/Samoa` (146 bytes) and `UTC` (111 bytes): verbatim IANA bytes
  (base64 constants in the script, provenance: PyPI `tzdata` package).
  Samoa's explicit transitions end in 1911 with the last type fixed at SST
  (UTC-11), which is still correct for the 2018 test dates; UTC has zero
  transitions and a single UTC type.
- `Europe/Berlin` (1452 bytes): 60 authentic historical transitions
  (1893-1996, embedded constants) plus 83 explicit transitions generated
  from the file's own POSIX footer rule
  (`CET-1CEST,M3.5.0,M10.5.0/3`, i.e. last Sunday of March/October at
  01:00 UTC) covering October 1996 through October 2037. The slim file
  alone is unusable here because the cxxtools `Tz` parser does not read
  the POSIX footer, so every 2018 date would wrongly resolve to CEST (+2).

Regenerate locally: `python generate_berlin_fat.py --all <tzdir>`
(single Berlin: `python generate_berlin_fat.py <out>`, legacy slim-input
mode: `python generate_berlin_fat.py <slim-berlin> <out>`).
The script asserts rule continuity, strict ordering and CET/CEST
alternation before writing; output was verified byte-identical to the
previously validated fixture (Berlin 1452 B / Samoa 146 B / UTC 111 B).

## Verification (done locally, no device needed)

1. Independent TZif re-parse: 143 transitions, strictly increasing,
   2018-10-28 01:00 UTC present, suite continues at 1996-10-27 CET.
2. Cross-check with CPython `zoneinfo` (`TZPATH` pointed at generated files):
   every `tz-test.cpp` vector matches (Berlin/Samoa local2utc + utc2local,
   ambiguous 02:30 hour with fold 0/1, November/August DST flags).
3. Replay of the cxxtools `Tz::toUtc`/`toLocal`/`offset` algorithms
   (including the ambiguity throw and early/late branches) against these
   files reproduces all six suites' expectations.
4. Generator self-check: `--all` output is byte-identical to the validated
   fixture, so switching from vendored binaries to test-time generation
   changes zero test bytes.
