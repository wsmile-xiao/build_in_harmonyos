# wireless-regdb 2026.05.30 adaptation notes

## Source

The recipe uses the immutable release archive from kernel.org. Both configured
URLs serve the same 31 KB archive with SHA256
`8a27bfc081bafed8c24dd70fab0d96f098e5a0bfcd08d3da672595f225ab8993`.

## Packaging

wireless-regdb is architecture-independent regulatory data, so no target C or
C++ compilation is required. The package installs the authoritative `db.txt`,
the compiled and signed `regulatory.db` files, and the upstream Python parser
and compiler under `share/wireless-regdb`.

The package has no standalone user command. Consumers locate the data through
the `WIRELESS_REGDB_DIR` and `WIRELESS_REGDB` build/run environment variables.

## Tests

The upstream release does not contain a formal test suite. It does contain the
authoritative text database, parser, compiler, and compiled database. The
recipe therefore performs deterministic domain validation instead of claiming
unavailable upstream tests.

The validator parses all 182 country records and 1,013 country permissions,
checks the published text and binary hashes, validates representative FCC,
ETSI, and JP DFS regions, and regenerates `regulatory.db` with the upstream
`db2fw.py`. The regenerated file must match the signed release payload byte for
byte. A malformed frequency range is also rejected to prove the parser's error
path.

## Local validation

- Upstream formal tests: not available (0 scenarios in the release archive).
- Source semantic validation: passed, 18/18 assertions.
- Direct `db2fw.py` regeneration: passed; output is byte-identical to the
  published `regulatory.db`.
- Native Conan 2.29.1 `conan create`: passed, including the packaged consumer
  validation with 18/18 assertions.
- Official OHOS aarch64 CI: not run yet.
- HarmonyOS PC real-device validation: not run; no device is attached.
