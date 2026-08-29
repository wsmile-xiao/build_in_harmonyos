# AutoDock Vina 1.2.7

## Source

- Upstream: https://github.com/ccsb-scripps/AutoDock-Vina
- Tag: `v1.2.7`
- Build system: the upstream Linux release Makefile

## OHOS adaptation

The upstream Makefile assumes `/usr` and `g++`. The Conan recipe redirects
those paths to the published Boost packages and the Conan compiler, disables
the upstream static-link default, adds an OHOS-compatible RUNPATH, and passes
the profile shell to `make`.

Boost 1.90.0.1 supplies the compiled libraries, but its published OHOS package
omits the `boost/log` and `boost/ptr_container` headers required by Vina. The
published OHOS Boost 1.84.0 package contains both components, so the recipe
uses it as a build-context header provider while retaining 1.90.0.1 for host
link libraries. To avoid ABI mismatches, the recipe puts the 1.90.0.1 include
directory first and the complete 1.84.0 include directory second as a
fallback, so all headers resolve while filesystem uses the matching 1.90 ABI.

Boost 1.90.0.1 headers use C++14 type traits, so the upstream C++11 flag is
raised to C++14; Vina's C++11 source remains source-compatible.

The shared include flags are defined in `build/makefile_common`; the recipe
patches that file directly so both Boost include directories receive `-I`.

The upstream `LDFLAGS` definition is also in `build/makefile_common`. The recipe
adds the Boost library RUNPATH there because OHOS does not honor
`LD_LIBRARY_PATH` for these binaries.

OHOS musl does not declare `pthread_setcancelstate`, which Boost 1.84.0
references from `boost/core/detail/sp_thread_sleep.hpp`. The recipe adds
Boost's official `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` compile-time switch on
OHOS to select the portable sleep path.

Boost.System is header-only since Boost 1.69. The upstream Makefile still
lists `-l boost_system` in `build/makefile_common`, so the recipe removes that
obsolete linker argument there for the published OHOS Boost packages.

The release contains no automated upstream test target. The Conan test package
therefore performs two real CLI assertions: `vina --version` and `vina --help`
(matching the upstream help's `Input:` section).

## Final real-device validation

- `conan create`: passed (OHOS 6.0 / armv8 / clang 15 / Release)
- `test_package`: 2/2 passed
- `vina --version`: passed
- `vina --help`: passed
