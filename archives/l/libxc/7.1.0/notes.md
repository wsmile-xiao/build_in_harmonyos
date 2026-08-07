# libxc 7.1.0 adaptation notes

## Scope

- Issue: #1903.
- Worktree: `D:\harmonyos\worktrees\libxc`.
- Branch: `feat/libxc-7.1.0`.
- Scope is limited to `archives/l/libxc/7.1.0/`.

## W0 dependency check

The core C library has no third-party Conan dependencies. The CMake build only
uses the C compiler and the standard math library. Optional Fortran, Python,
CUDA, and HIP interfaces are disabled in the default recipe so missing optional
toolchains do not block the base package.

The upstream CMake testsuite depends on a Python interpreter and pytest. It is
kept as a deferred verification path through the `with_tests` recipe option
instead of being mixed into the default package build.

## Source and build system

The official GitLab archive was downloaded from
`https://gitlab.com/libxc/libxc/-/archive/7.1.0/libxc-7.1.0.tar.gz` and
verified with SHA256
`403499330a8ff7e1aa27d51c2b14cc5bc4e49ec02fd115031ab8c8a91465bb51`.

The release ships both Autotools and CMake files. Upstream README documents
CMake as the path that supports static/shared libraries, namespaced headers,
Fortran 2003, CUDA/HIP, and Python bindings. The recipe therefore uses CMake
and installs the core C library target `Libxc::xc`.

Default build choices:

- `BUILD_SHARED_LIBS=OFF` and `BUILD_FPIC=ON`.
- `ENABLE_FORTRAN=OFF`, `ENABLE_PYTHON=OFF`, `ENABLE_CUDA=OFF`,
  `ENABLE_HIP=OFF`.
- `BUILD_TESTING=OFF`; enable with `-o libxc/*:with_tests=True` when the
  target environment has Python/pytest.
- `CMAKE_INSTALL_LIBDIR=lib` to avoid `lib64` drift on OHOS.
- `NAMESPACE_INSTALL_INCLUDEDIR=/` so consumers can include `<xc.h>`.

The first OHOS shared-library attempt reached the final link step but failed
when CMake tried to create the `libxc.so` symlink for the versioned SONAME:
`cmake_symlink_library: Permission denied`. The default package therefore uses
a static core C library for this PR. A shared build should be revisited with an
OHOS-specific no-versioned-symlink patch if downstream requires `libxc.so`.

## Tests

The upstream CMake testsuite contains four CTest entries: `python-tests`,
`special-functions`, `api`, and `distinct`. Because `BUILD_TESTING=ON` requires
Python/pytest before CMake generation can complete, the default build defers
that suite until a real OHOS/shadow CI window with those tools is available.

The `test_package` links `Libxc::xc` and exercises public C APIs:

- `xc_version` and `xc_version_string` verify the installed 7.1.0 package.
- `xc_number_of_functionals` checks the installed functional inventory.
- `xc_func_init`, `xc_func_get_info`, `xc_lda_exc`, and `xc_func_end` initialize
  `XC_LDA_X`, evaluate three density points, and validate finite, ordered
  exchange energy output.

## True-device validation

The package was validated directly over SSH on HarmonyOS PC
`10.62.189.79:2222` as `currentUser`; shadow CI was not used.

Command:

```sh
CI_PACKAGES="archives/l/libxc/7.1.0" zsh ci/conan/build_and_test.sh
```

Result: PASS.

- L0: pass, all quality gates passed.
- L1: pass, `conan create` executed `test_package` and printed
  `libxc 7.1.0 API smoke passed`.
- L2: skip/non-blocking, `xc-info --version/--help` is not supported.
- L4: pass, no patches.
- L5: pass, packaged `bin/xc-info`, headers, `lib/libxc.a`, CMake config, and
  `lib/pkgconfig/libxc.pc`.
- `conan_build_libxc_7.1.0.log` SHA256:
  `f716a84d07e59c93e052be52420a2267d938f5b284315995985e7134b0034eda`.

## Local front-load validation

This Windows host does not have `conan`, `cmake`, or `python` in PATH. Front-load
validation is therefore limited to source checksum/build-system inspection and
syntax checks using the bundled Codex Python runtime. Full `conan create` and
`ci/conan/build_and_test.sh` verification must run on OHOS/shadow CI.

## Next OHOS/shadow CI commands

Default single-package verification:

```sh
CI_PACKAGES="archives/l/libxc/7.1.0" zsh ci/conan/build_and_test.sh
```

Optional upstream CTest verification, if Python/pytest is available:

```sh
cd archives/l/libxc/7.1.0
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos \
  -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing -o libxc/*:with_tests=True
```

Shadow CI runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/libxc/7.1.0
```
