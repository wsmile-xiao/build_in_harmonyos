# utest native test report

- Native HarmonyOS/aarch64, run `utest-20261004-r007`, unique launch 1.
- Official registered CTest scenarios: 13/13 PASS, 0 failed/skipped scenarios.
- Each suite exposes 2178 internal cases; 2168 PASS plus 10 intentional Todo
  skip-behavior controls. Do not count repeated/random-order/sanitizer runs as
  28314 independent unit cases, or claim zero internal skipped controls.
- Installed-header consumer: 2/2 PASS; OHOS monotonic timer: 1/1 PASS.
- Exact transfer, receipt/WAL validation, AFTER, owned processes 0 and
  release/postrelease all PASS. Previous r001-r006 remain real failures.
- Formal native Conan create and local CI simulation PASS in formal-utest-r001;
  input hashes unchanged. Aggregate finish remains PARTIAL_POST_W3 RC1 for
  baseline knowledge/scope/legacy packaging checks; do not claim aggregate PASS.
- Current-HEAD platform AI Review and CI remain separate, not yet claimed PASS.
