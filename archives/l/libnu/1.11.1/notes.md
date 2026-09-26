# libnu 1.11.1 adaptation notes

- Upstream: https://bitbucket.org/alekseyt/nunicode (tag 1.11.1), MIT, Unicode 13.0.
- Source: https://bitbucket.org/alekseyt/nunicode/get/1.11.1.tar.gz
  sha256 09b4be81cb5a5086cc687a4a3a5fbed7691e4fbdedad29789aba7ee124d2d1ad.
- Build: CMake, single static target `nu` (libnu/CMakeLists.txt always STATIC);
  install exports `nunicode::nu` + headers to include/libnu.
- Upstream tests (must run, not skippable):
  - tests/CMakeLists.txt lists 24 entries incl. main.c driver; real modules are
    22 `*_test.c` files + 2 generated ducet files = 24 modules. Preflight log
    shows the `units` binary prints `OK - 103 tests` on success, so the recipe
    now parses that summary line for HMBS_UPSTREAM_TEST_RESULT counts
    (discovered/executed/passed = N from the log). The file-based module
    count is kept only as a fallback that fails loudly when the summary line
    is missing, so stale numbers can never silently pass.
  - Harness is assert-based: `units` prints `OK - N tests` on success,
    non-zero exit on failure. Empty output, missing binary, or missing
    summary line is treated as failure, never as pass.
- test_package: consumer C program links `nunicode::nu`, calls nu_utf8_read /
  nu_validate / nu_version across 5 CASE checks; each prints `CASE PASS`.
- This round fixed the preflight evidence gate: archives/l/libnu/1.11.1 did not
  exist, so HMBS reported "cannot read archive tree". Created the full recipe
  tree (conanfile.py + conandata.yml + manifest.yaml + notes.md +
  test_package/) so the next preflight can run conan create end to end.
