# mdds/3.2.1 — OpenHarmony PC (aarch64)

A collection of multi-dispatch data structure libraries for C++.
Header-only since 2.0; this version requires C++20.

- **Upstream**: <https://gitlab.com/mdds/mdds> (tag `3.2.1`)
- **Source tarball**: <https://gitlab.com/mdds/mdds/-/archive/3.2.1/mdds-3.2.1.tar.gz>
- **SHA256**: `2de944aee7d6f61ac648b0b10042618a208f9fd2701dd42059874d987a479bb4`
- **License**: MIT

## Package type

`header-library` — mdds ships only headers (34 `*.hpp` under `include/mdds/`).
No `.a` / `.so` / `.dylib` is produced by this recipe or by upstream.

The public headers `node.hpp` and `quad_node.hpp` transitively include
`boost/intrusive_ptr.hpp`, so `boost/1.90.0` is a real (header) requirement.

`package_id` is cleared — the package id does not depend on compiler /
build-type toolset details, since no ABI-sensitive code is built here.

## Build system

Upstream ships a CMake build tree whose sole purpose is to run the test
suite under `test/` and install headers.  Since the library itself is
header-only and produces no build artifact, the recipe's `build()` is a
no-op; the upstream test suite is exercised by `test_package/` instead
(see below).

## Tests

`test_package/` compiles and runs on the real OHOS aarch64 `clang++` and
exercises two core data structures — `flat_segment_tree` and `trie_map` —
with real `insert` / `set` / `query` / `erase` operations and `assert`s on
the results (not a bare `#include`).
