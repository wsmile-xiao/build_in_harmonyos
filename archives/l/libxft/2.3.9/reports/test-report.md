# libxft 2.3.9 test inventory

## Upstream tests

- Registered upstream tests: 0
- Expected result: 0/0
- Evidence: the release contains no test directory, Automake test target, or
  Meson `test()` registration. The recipe still executes `meson test`.

## Added consumers

- `libxft_api_surface`: 77 typed public-symbol checks plus two runtime checks.
- `libxft_name_contract`: 16 display-independent positive and negative checks.
- Actual result: 2/2 independent programs, 95/95 assertions.

## Current target result

- Upstream tests: 0/0 (the upstream Meson project reports `No tests defined`).
- Added consumers: 2/2.
- Shared/static variant executions: 4/4.
- Assertions: 95/95.
- Endpoint: `10.62.148.108:2222`.
- Run: `libxft-2.3.9-w3-r26-21c8cbbf`, launch count 1.
- Evidence SHA-256:
  `446fb1e10393f2d961d4bde9b258e5b707e754e6a765b9e4e8b73c61e3b4e6c7`.
- Transaction result:
  `F:/HarmonyPC/libxft-239/w3-r26-21c8cbbf/collection/transaction-result.json`.

The result is bound to the repaired mode-policy candidate. Its production and
test-package directed matrix passed 14/14 before the fresh target transaction.
The transaction also verified release, zero owned remote processes, and two
postrelease clean scans.

## Official finish

- Conan verify: PASS.
- Finish local CI: PASS; `.ci-result.json` exit code 0 and integrity hash valid.
- Aggregate finish: `PARTIAL_POST_W3` because only repository-wide knowledge
  baseline and legacy `packaging/` readiness checks failed after W3.
- No Conan/CNB upload was performed.
