# curlcpp

curlcpp is an object-oriented C++11 wrapper for libcurl (C API).

## HarmonyOS PC adaptation

- Builds shared `libcurlcpp` from the official 3.1 source against the
  Conan-provided libcurl (`curl/8.15.0.1`, `find_package(CURL)`).
- Removes the `CURLOPT_CLOSEPOLICY` / `CURLOPT_OBSOLETE72` option shims that
  no longer compile with libcurl 8.10+ (mirrors upstream fix `bc38005`,
  also backported by Homebrew).
- Upstream ships no automated test suite (`test/` holds only
  network-dependent demo programs with no ctest registration), so the
  example tree is not built; the Conan consumer verifies 6 real API
  assertions fully offline (never calls `perform()`).

## Consumer verification

The Conan consumer links `curlcpp::curlcpp` and checks easy-handle
construction (plain and stream-backed), transfer option setting, form
composition, multi add/remove lifecycle, and the `make_option` helper.
The HarmonyOS PC run completed this consumer test successfully.

## Reference

- https://github.com/JosephP91/curlcpp
- https://josephp91.github.io/curlcpp
