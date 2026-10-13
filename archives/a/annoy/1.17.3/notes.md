# annoy 1.17.3 adaptation notes

- Upstream source is the official GitHub release tarball `v1.17.3`, byte-verified
  by the SHA256 recorded in `conandata.yml`.

- **annoy is a header-only C++ library.** The complete search implementation is
  `src/annoylib.h`; there is no compiled C++ library upstream. Upstream's own
  `CMakeLists.txt` models this with an `INTERFACE` target and installs
  `include/annoy/{annoylib.h,kissrandom.h,mman.h}`. This recipe therefore
  packages the upstream header-only library as-is and needs **zero patches** —
  the POSIX `<sys/mman.h>` path that `annoylib.h` uses for on-disk index builds
  is provided by the OHOS musl sysroot.

- **Upstream test suite and why it is not run directly.** The `test/` directory
  holds 107 pytest functions, but every one of them drives the CPython extension
  module `annoy.annoylib` built from `src/annoymodule.cc` — a Python binding,
  not part of the C++ library surface. They cannot be executed against a C++
  package without building a CPython extension for the target. The upstream C++
  entry point that genuinely exercises `annoylib.h` is
  `examples/precision_test.cpp`, which builds an index and then runs 1000
  precision queries across four `search_k` limits. `build()` compiles that
  upstream source unmodified with the OHOS toolchain and executes it through the
  profile emulator; the process exit code gates the build.

  Upstream's example defaults to `f=40, n=1000000`, which is far too slow under
  emulation; the example accepts both as `argv`, so it is invoked as
  `precision_test 8 2000`. Measured result: `limit: 10 -> 95.93%`,
  `limit: 100/1000/10000 -> 100.00%`.

- **Multithreading.** `annoylib.h` only exposes
  `AnnoyIndexMultiThreadedBuildPolicy` when `ANNOYLIB_MULTITHREADED_BUILD` is
  defined (upstream `setup.py` defines it for every Python 3 platform, and its
  own `s_compile_cpp.sh` example does too). Because of that, this recipe declares
  `pthread` (and `m`) as system libraries so consumers can enable it.

- **`cppstd`.** `configure()` pins `cppstd=14`, matching upstream's
  `-std=c++14`. `CMAKE_POLICY_VERSION_MINIMUM=3.15` (aligned with upstream's own
`cmake_minimum_required(3.15...3.25)`) is set for safety against
  upstream's `cmake_minimum_required(VERSION 3.15...3.25)`.
