# libxcb 1.16 HarmonyOS adaptation notes

## Scope

- Issue: pending. Project files and source task context did not contain a concrete issue number.
- Branch: `feat/libxcb-1.16`
- Worktree: `D:\harmonyos\worktrees\libxcb`
- Package path: `archives/l/libxcb/1.16`
- Upstream version: libxcb 1.16. This is the right upstream version for the libX11 1.8.10 requirement `xcb >= 1.11.1`.

## W0 Dependency Check

| Dependency | Purpose | ohpcd status |
|---|---|---|
| `xcb-proto/1.17.0` | XML protocol descriptions and `xcbgen` Python generator | available |
| `xorgproto/2025.1` | X11 protocol headers used through `libxau`'s `X11/Xauth.h` include chain | available |
| `libxau/1.0.11` | X authority file support | available |
| `libxdmcp/1.1.5` | Optional XDM-AUTHORIZATION-1 support; enabled because the package is available | available |
| `check/0.15.2` | Upstream `tests/check_all` unit test framework | available |
| `pthread-stubs/0.4` | Upstream pkg-config metadata for platforms missing pthread symbols | not available in ohpcd |

`pthread-stubs` is not modeled as a Conan dependency for OHOS. The local old
archive notes for `libpthread-stubs/0.4` state that OpenHarmony already provides
the pthread functions and that the package only installs an empty
`pthread-stubs.pc`. The libxcb recipe uses the project OHOS Autotools triplet
`aarch64-unknown-linux-ohos`; upstream treats `linux*` hosts as pthread-capable,
so configure does not require `pthread-stubs`.

## Build System

- Build system: Autotools release tarball with pregenerated `configure` and `Makefile.in`.
- Source URL: `https://xcb.freedesktop.org/dist/libxcb-1.16.tar.gz`
- sha256: `bc0f75f84b28e6496a19a1d094d7e47def861a50cb7cce5b23b62eecdc2a4479`
- Code generation: `src/c_client.py` reads XML from `xcb-proto` through `PKG_CONFIG_PATH` and `PYTHONPATH`.
- Enabled outputs: shared `libxcb.so.1` plus the default generated extension libraries.

## Adaptation

- Added Conan recipe, source metadata, patches, and non-empty `test_package`.
- Added `patches/0001-support-ohos-configure.patch`:
  - teaches upstream `config.sub` to accept the `linux-ohos` OS component;
  - avoids defining Linux abstract sockets for `linux-ohos`;
  - moves Autoconf `config.status` temporary directory creation under `TMPDIR` with `umask 022`.
- Added `patches/0002-use-tmpdir-in-display-test.patch` so the upstream
  `parse_display_unix` test uses `TMPDIR` instead of hard-coded `/tmp`, which
  is read-only on the validation device.
- Added `patches/0003-fix-present-pc-requires.patch` to add `xcb-dri3` to
  `xcb-present.pc.in`'s `Requires.private`, matching the generated
  `present.h` include chain and satisfying upstream `check-pc-requires`.
- The patch intentionally does not touch `configure.ac`; changing Autotools
  inputs in the release tarball makes `make` try to run missing `aclocal-1.16`.
- For OHOS, the recipe exports `CK_FORK=no` for Check tests, sets
  `TMPDIR`/`TMP`/`TEMP`, uses LLVM binutils from the configured clang
  directory, and uses a recipe-local `pkg-config` shim because no `pkg-config`
  package is published in ohpcd.
- `xorgproto` is retained as a direct transitive header requirement and exported
  from the core `xcb` component as `xorgproto::xorgproto`, matching the existing
  Xorg recipe pattern used by `libxau`, `libxdmcp`, `libice`, and `xtrans`.
- Uses `xcb-proto/1.17.0` through that package's build environment. Do not
  activate `xcb-proto` in `PkgConfigDeps`: the Conan-generated replacement
  `xcb-proto.pc` lacks upstream's `xcbincludedir` and `pythondir` variables,
  while the package-provided `share/pkgconfig/xcb-proto.pc` has both.
- Added software-level `archives/l/libxcb/commands.json` for repository
  metadata. Because libxcb is a library package and does not install
  command-line executables, the entry uses `"type": "library"` and
  `"binary": false` without a `commands` list.

## Tests

Upstream tests:

- `check-pc-requires` validates installed `xcb*.pc` metadata.
- `tests/check_all` is built when `check/0.15.2` is present and exercises public APIs such as `xcb_parse_display`.

Consumer test:

- `test_package/test.c` links `libxcb::xcb`.
- It calls `xcb_parse_display()` and links the generated
  `xcb_big_requests_id` symbol without dereferencing the opaque
  `xcb_extension_t` internals.
- It does not require a running X server.

## Local Validation

Executed local preflight commands:

```powershell
python -m py_compile archives/l/libxcb/1.16/conanfile.py archives/l/libxcb/1.16/test_package/conanfile.py
git diff --check -- archives/l/libxcb
conan inspect archives/l/libxcb/1.16
conan graph info archives/l/libxcb/1.16 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
conan export archives/l/libxcb/1.16
conan install archives/l/libxcb/1.16 -of C:\Users\ylinz\AppData\Local\Temp\libxcb-install-check2-019fcf54 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
git apply --check patches/0001-support-ohos-configure.patch against upstream libxcb-1.16
git apply --check patches/0002-use-tmpdir-in-display-test.patch against upstream libxcb-1.16
git apply --check patches/0003-fix-present-pc-requires.patch against upstream libxcb-1.16
```

All commands above passed. The `conan install` generator output no longer
contains a generated `xcb-proto.pc`; `conanbuildenv-release-armv8.sh` points
`PKG_CONFIG_PATH` to `xcb-proto`'s package-provided `share/pkgconfig` directory
and sets `PYTHONPATH` to its `lib/python3/site-packages` directory.

Full OHOS/shadow CI command:

```sh
CI_PACKAGES="archives/l/libxcb/1.16" zsh ci/conan/build_and_test.sh
```

Software-level command metadata: `archives/l/libxcb/commands.json` is present
for `libxcb/1.16`; it declares the package as a library with no command-line
executables.

Final OHOS single-package validation after the contest CI PATH fix, AI review
fixes, and configure case patch correction:

```text
Log: /storage/Users/currentUser/libxcb-ci-full-bootstrap-fix.log
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Build Summary: Success 1, Failed 0
```

Latest OHOS single-package validation against the current `origin/main` CI
script after adding the xorgproto component dependency fix:

```text
Log: /storage/Users/currentUser/libxcb-ci-full-xorgproto-component-fix.log
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Build Summary: Success 1, Failed 0
```

Notable fixes found during device validation:

- `check_all` initially failed because Check fork-mode IPC and libxcb's
  Unix-display test tried to use temp locations that are restricted on OHOS.
  `CK_FORK=no` plus the TMPDIR-aware test patch fixed it.
- `check-pc-requires` initially reported `xcb-present missing xcb-dri3`;
  `0003-fix-present-pc-requires.patch` fixed the generated pkg-config
  metadata.
- Conan 2 rejected unused direct requirement `xorgproto` on some official
  workers even when `cpp_info.ignored_requires` was set. To stay compatible
  across worker Conan versions, the recipe now exports `xorgproto::xorgproto`
  from the core `xcb` component as a transitive header dependency.
- Contest CI later ran with a minimal base `PATH` and failed before configure
  feature checks because Conan's generated env scripts could not find
  `printenv`, and upstream `configure` could not find `sed`/`expr`. The recipe
  now prepends `/data/service/hnp/bin`, `$HOME/usr/local/bin`, `/bin`, and
  `/usr/bin` to the Python process environment before invoking Autotools. Do
  not also add those paths through `Environment.prepend_path("PATH", ...)`:
  the contest CI worker reproduced a Conan `EnvVars.apply()` `KeyError:
  'PATH'` at `build_env.vars(self).apply()` when PATH was modeled this way.
- Validation after removing the Conan `PATH` env overlay:
  - Minimal official-style PATH direct Conan create passed:
    `/storage/Users/currentUser/libxcb-direct-keyerror-fix.log`.
  - Full L0-L5 single-package CI script passed:
    `/storage/Users/currentUser/libxcb-ci-full-keyerror-fix.log`.
- AI review later flagged two portability issues in the OHOS configure setup.
  The recipe now derives `--build` and `--host` from Conan build/host settings
  and normalizes Conan's raw `aarch64-ohos` triplet to
  `aarch64-unknown-linux-ohos`; the raw form made libtool detect shared library
  support as unavailable during review-fix testing.
- `CONFIG_SHELL` and `SHELL` now resolve to an existing executable from the
  environment or `PATH`, falling back to `sh` only after checking common OHOS
  shell locations. This avoids assuming `/data/service/hnp/bin/bash` exists.
- `test_package/test.c` frees `got_host` before returning from the
  `xcb_parse_display()` failure path.
- Validation after the AI review fixes:
  - Minimal official-style PATH direct Conan create passed:
    `/storage/Users/currentUser/libxcb-direct-review-fix2.log`.
  - Full L0-L5 single-package CI script passed:
    `/storage/Users/currentUser/libxcb-ci-full-review-fix.log`.
- Contest CI #13521 later reproduced the official worker's minimal base `PATH`
  more strictly. Although the recipe mutates `os.environ["PATH"]`, Conan's
  default `self.run()` wrapper sources generated `conanbuild*.sh` scripts before
  running `configure`, and those generated scripts call `printenv` before
  applying the profile's `PATH`. The recipe now patches generated activation
  scripts in `self.generators_folder` to prepend the OHOS tool paths before the
  first `printenv`; the test package does the same before CMake configure/build
  and before `conanrun` execution. The main recipe also rewrites generated
  `SHELL`/`CONFIG_SHELL` exports to the resolved executable shell.
- Real-device verification with the official-style minimal PATH then exposed a
  bad zero-context hunk in `0001-support-ohos-configure.patch`: the
  `linux-ohos*)` configure case was inserted before the existing `mingw*)`
  terminator, producing `syntax error: unexpected ')'`. The hunk now carries
  enough context to insert the OHOS branch after `mingw*) ... ;;`.
- Validation after correcting the configure case hunk:
  - Minimal official-style PATH direct Conan create passed:
    `/storage/Users/currentUser/libxcb-conan-create-minpath-bootstrap-fix.log`.
  - Full L0-L5 single-package CI script passed:
    `/storage/Users/currentUser/libxcb-ci-full-bootstrap-fix.log`.
- Official CI #14595 then failed before `conan create` because the old main
  `ci/conan/build_and_test.sh` pre-download step expanded an unset `BUILD_DIR`
  whenever a package had `conandata.yml`. This was a package-agnostic CI script
  regression. After rebasing to the fixed main script, the pre-download cache
  uses `${pkg_dir}/predl_cache`, and libxcb keeps `conandata.yml` so source
  pre-download and retry remain active.
- Reproducing the fixed main CI script on the 33332 validation device then
  reached `test_package`, where CMake initially failed because the OHOS profile
  named `/data/service/hnp/bin/clang` but this device only has
  `$HOME/usr/local/bin/clang`. The test package now patches generated
  `conan_toolchain.cmake` to use `clang`/`clang++` from `PATH` only when the
  configured compiler path is missing. Validation passed in
  `/storage/Users/currentUser/libxcb-ci-full-originmain-conandata-lfconfig-testpkg-compiler-fix.log`.
- Official CI #15120 later failed at `package_info()` because some worker Conan
  versions do not honor `cpp_info.ignored_requires` for suppressing unused
  direct requirement validation. The recipe now follows the existing Xorg
  package pattern and exports `xorgproto::xorgproto` from the core `xcb`
  component as a transitive header dependency. Full L0-L5 validation passed in
  `/storage/Users/currentUser/libxcb-ci-full-xorgproto-component-fix.log`.
