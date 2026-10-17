# Boost.JSON 1.84.0 HarmonyOS adaptation

The recipe bypasses Boost.Build and compiles `libs/json/src/src.cpp` directly
with the OHOS C++17 toolchain. The consumer test parses a JSON object, reads
typed values, mutates an array, and serializes the result.

The upstream Boost.JSON 1.84.0 test inventory contains 50 `.cpp` source
files under `libs/json/test/`. The OHOS validation compiles every one of
them — including the four sources the upstream CMakeLists.txt treats as
standalone targets (`limits.cpp`, `no_exceptions.cpp`, `intrusive_macros.cpp`,
`cmake_install_test/main.cpp`) and the three Ryu test sources — into the
build's `objects/test/` tree using `clang++ -std=c++17 -DBOOST_JSON_SOURCE`.
The main binary reports 42 suites and 0 failures; the companion target also
exits 0. A single patch (`patches/0001-fix-cmake-install-test.patch`) fixes
an upstream API bug in `cmake_install_test/main.cpp` (the test calls
`boost::json::to_string(value)`, which doesn't exist in 1.84.0 — only
`to_string(kind)` does — so the file is patched to use `boost::json::serialize`,
which accepts `value const&`).
