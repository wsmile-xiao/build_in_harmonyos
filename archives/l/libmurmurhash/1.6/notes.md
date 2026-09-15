# libmurmurhash 1.6

## Source

libmurmurhash 1.6 official GitHub tag archive.

https://github.com/kloetzl/libmurmurhash/archive/refs/tags/v1.6.tar.gz

SHA256:

a19a92769e3bf022d86a0715f2ac7ed535c853952b80de522e8430e0bab35c3b

Upstream is a portable MurmurHash implementation in pure C (public domain,
NOLICENSE). It provides the three MurmurHash3 variants plus the deprecated
original API. No external runtime dependencies.

## Build

Vendored CMake build, no autotools chain. Four bootstrapping attempts
on the HMBS preflight image: `autoreconf` is not on PATH, a
direct-`cc` attempt read a stale `tools.build:compiler_executables` value
(`//data/service/hnp/bin/clang`, not executable on the host), plain
CMakeToolchain inherits that same broken `CMAKE_C_COMPILER`, and a
`tc.cache_variables["CMAKE_C_COMPILER"]` override proved ineffective --
the preflight log shows the probe found a working clang yet CMake still
received `/data/service/hnp/bin/clang`, i.e. the OHOS toolchain logic
re-resolves the compiler from profile conf during generate() and drops
the user cache value. The library
is two pure-C files with no `config.h` dependency, so build() writes a
minimal CMakeLists.txt (library + mmh + mmh_old, precedent
murmurhash3/0.0.1) and generate() probes PATH-first for a working
compiler (conf value demoted to last resort), runs CMakeToolchain for
flags/sysroot, then patches the emitted conan_toolchain.cmake replacing
only exact stale compiler path substrings (never flags/sysroot).
test_package generate() patches the same way. HMBS guarantees cmake/make/ninja on PATH.

The library is pure C with no external library dependencies.

## Tests

Upstream tests are test/mmh.c (new lmmh_* interface) and test/mmh_old.c
(deprecated MurmurHash3_* interface), executed exactly as upstream
`make check` does: each binary hashes test/almostempty and its stdout is
compared against test/almostempty.hash. build() runs both CMake-built
binaries via subprocess (no shell pipes), asserts both fixtures are
non-empty (anti empty-vs-empty false pass), asserts both outputs are
non-empty, then byte-compares. Result is emitted as
HMBS_UPSTREAM_TEST_RESULT (discovered=2) and persisted to
res/upstream_test_result.json for test_package re-emit on cache hits.

The Conan test_package additionally validates:

- public header consumption
- x86_32 hashing determinism and seed sensitivity
- x86_32 input sensitivity
- x86_128 hashing determinism
- x64_128 hashing determinism
- deprecated MurmurHash3_x86_32 API compatibility
- zero-length input handling
