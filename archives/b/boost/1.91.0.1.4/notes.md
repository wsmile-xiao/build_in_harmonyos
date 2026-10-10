# Boost 1.91.0.1.4 for libosl on HarmonyOS PC

This is a new suffix of the published `boost/1.91.0.1.3` selective component
package, not an overwrite of that revision. `libosl/0.8.0` failed on the
device when including `boost/accumulators/accumulators.hpp`: its include root
was correct but the published Boost package did not contain Accumulators.

## Component and source contract

- Keep the preceding compiled component set; add the official header-only
  `Boost::accumulators` CMake target and its public compiled
  `Boost::serialization` dependency to Conan `package_info()`.
- Include Accumulators in both production and upstream-test component lists.
- Use the official `boost-1.91.0-1-cmake.tar.xz` release asset and SHA-256
  `cc5dc5006ecbdf0051f90979be31b4eee5987d9ae14ae9fb9c03cfa43fa3cdad`.
  If device access to GitHub times out, `BOOST_SOURCE_ARCHIVE` may point to
  an independently transferred byte-identical archive; `source()` verifies
  the exact hash before extraction. The default fetch remains the official URL.
- The existing Asio header staging and other published components remain
  unchanged; this suffix does not introduce Boost.Context on OHOS.

## OHOS build and test details

- Boost.UUID's upstream Clang default links a separate `libatomic`, absent
  from this OHOS toolchain. Set `BOOST_UUID_LINK_LIBATOMIC=OFF` on OHOS; do not
  mask unresolved atomics. The complete test closure links and runs afterward.
- Build the upstream component-test tree with static Boost.Test, as the
  Accumulators Jamfile explicitly requires. Its legacy `init_unit_test_suite`
  programs receive `main` from the static framework. The production package
  remains shared.
- The CMake Jamfile importer ignores `run tail.cpp` because that line has
  inline target requirements. Patch `libs/accumulators/test/CMakeLists.txt`
  to register the unmodified upstream `tail.cpp` via `boost_test`, including
  header-only Boost.Foreach. The official `valarray.cpp` target explicitly
  says it fails under libc++; it is not applicable to this Clang/libc++ build.

## Device validation

W3 transaction `boost-w3-20261004T141208Z` on the inventoried device
`10.62.201.39:2222` and boot ID
`c308aed3-ef7f-4a31-8897-e29443b03b71` returned
`W3_PASS upstream=66/66 consumer=9/9` after `conan create` exit 0,
release/postrelease, and independent receipt-chain validation. Upstream
breakdown: 63/63 main CTest (48 Accumulators, 14 ProgramOptions, one
Multiprecision), 1/1 Iostreams, 1/1 Regex, and one unmodified Graph leaf in
test_package. The nine consumer tests include actual Accumulators mean/count
and the prior compiled-component contracts. The authoritative device log was
read back to task evidence as `conan-create.log`, SHA-256
`92a4b9b668abc08e23dc4dbf72fdf291fbc521dd9552375687db9465d9ae9010`.
This is device evidence, not a claim that competition-worker CI passed.

As in the published base suffix, the large Boost.Log upstream suite is not
part of the selected build-tree gate; the real file-sink runtime consumer
remains. This is disclosed rather than counted as an upstream suite PASS.
