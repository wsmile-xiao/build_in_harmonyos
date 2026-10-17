# qcbor

QCBOR - comprehensive, powerful, commercial-grade CBOR (RFC 8949) encode/decode library in pure C99.

- Upstream: https://github.com/laurencelundblade/QCBOR
- Adapted version: 1.4 (branch feat/qcbor-1.4, task 13885, activity 6)
- Build system: CMake (upstream also ships a Makefile); no external dependencies
- Upstream tests: 77 registry entries executed via the qcbortest aggregator
  (75 run / 0 failed on device; 2 entries are upstream TEST_ENTRY_DISABLED)
- Consumer test: test_package/consumer.c CBOR map encode/decode round-trip
- Special handling: backport of upstream PR #313 (pbBreak initialization,
  post-v1.4 fix); E077 signing + exec-gate retry for on-device test execution
