# curlcpp 3.1 HarmonyOS PC adaptation notes

## Scope

- Upstream source: curlcpp 3.1 release archive
  (`https://github.com/JosephP91/curlcpp/archive/refs/tags/3.1.tar.gz`,
  sha256 `ba7aeed9fde9e5081936fbe08f7a584e452f9ac1199e5fabffbb3cfc95e85f4b`,
  with Homebrew formula cross-check).
- curlcpp is an object-oriented C++11 wrapper for libcurl. Formal package:
  shared `libcurlcpp` plus public headers and CMake package config
  (`curlcpp::curlcpp`).
- Build system: CMake. Declared Conan dependency: `curl/8.15.0.1`
  (provides `CURL::libcurl` via `find_package(CURL)`; `CURLCPP_USE_PKGCONFIG`
  stays `OFF`).
- `BUILD_TEST` stays `OFF`: upstream `test/` holds 7 network-dependent
  example programs with no ctest registration (see audit below), so the
  example tree is not built.

## Dependency status

- W0: the only build dependency is `curl/8.15.0.1`, whose recipe exists
  in-tree at `archives/c/curl/8.15.0.1/`. Registry availability
  (`conan download curl/8.15.0.1 --only-recipe`) is verified on the
  HarmonyOS PC preflight; if the recipe is missing there, this adaptation
  blocks on publishing it first (R36).

## libcurl 8.10+ compatibility fix

- curlcpp 3.1 `include/curl_easy.h` carries `CURLOPT_OBSOLETE72` /
  `CURLOPT_CLOSEPOLICY` option shims. libcurl 8.10 removed the
  `CURLOPT_OBSOLETE72` enum value (now plain-int macro `9999`), so the shim
  no longer compiles against our `curl/8.15.0.1` dependency.
- Fix: `patches/0001-include-curl-easy-h.patch` removes the shim block,
  mirroring upstream fix commit `bc38005` (also backported by Homebrew for
  the same failure). Same class of fix as the in-tree `curlpp/0.8.1`
  `CURLOPT_CLOSEPOLICY` patch (E081 family).
- No `__OHOS__` platform macro is introduced; the patch is pure C++ and
  platform-independent.

## Upstream tests

- Audited upstream `3.1` tree (top `CMakeLists.txt`, `test/CMakeLists.txt`,
  all 7 `test/*.cpp`): no `enable_testing()` / `add_test()` /
  `add_custom_target(check)` anywhere; the 7 test programs
  (cookie/custom_request/easy/easy_info/header/recv_header/multi) are
  demos whose `main()` performs live requests against public sites
  (e.g. `http://www.google.it`) with no assertions.
- Conclusion: no automated upstream suite exists; recipe and test_package
  both emit `HMBS_UPSTREAM_TEST_RESULT` with `status:"no_tests"`
  (discovered/executed/passed 0 plus audit reason). Full audit in
  `test_package/MANIFEST.yml`.
- The falsifiability note is honored structurally: the consumer binary
  prints per-case `PASS:`/`FAIL:` lines plus a `RESULT: P passed, F failed`
  trailer, and `test()` raises when the trailer is absent or any case
  fails, so a silently-skipped run cannot be reported as passed.

## Consumer verification

- `test_package/test.cpp` exercises 6 real curlcpp APIs without any
  network transfer (`perform()` is never called): default `curl_easy`
  construction, option setting (`CURLOPT_URL`/`CURLOPT_FOLLOWLOCATION`/
  `CURLOPT_TIMEOUT`), stream-backed construction via
  `curl_ios<std::ostringstream>`, `curl_form` + `curl_pair` composition,
  `curl_multi` add/remove lifecycle, and the `make_option` helper.
- Counts (6 cases) are parsed from the binary's own `RESULT:` trailer and
  reported via `HMBS_TEST_PACKAGE_RESULT` with `discovered`/`passedCount`.

## Contest path

- Path A (basic adaptation): first-time Conan 2 recipe for curlcpp 3.1; no
  upstream contribution is claimed.

---

**适配日期**: 2026-09-11
**最终状态**: built（待真机预检回填实测证据）
