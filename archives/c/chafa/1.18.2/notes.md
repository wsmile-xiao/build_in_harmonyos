# chafa 1.18.2 HarmonyOS adaptation notes

## Scope

- Issue: 1924
- Worktree: `D:\harmonyos\worktrees\chafa`
- Branch: `feat/chafa-1.18.2-1924`
- Package path: `archives/c/chafa/1.18.2`

## W0 dependency check

- Required upstream dependency: `glib-2.0 >= 2.58`.
- Conan dependency selected: `glib/2.84.0.1`.
- `glib/2.84.0.1` is present in the current `origin/main` worktree and is sufficient for the upstream version requirement.
- GLib pulls its own `pcre2` dependency; chafa does not need a direct pcre2 requirement.
- Direct `conan download ... -r=ohpcd --only-recipe` could not be executed on this Windows host because `conan` is not installed on PATH or in the bundled Python runtime.

## Source and build-system analysis

- Final source URL: `https://hpjansson.org/chafa/releases/chafa-1.18.2.tar.xz`
- sha256: `0b8d9ba9f347e8b6c0c71878217c9b0e478b4a42aa4babea0bf20840567239c2`
- Build system: Autotools release tarball with generated `configure`.
- Upstream `configure` supports `--without-tools`; command-line tools require `freetype2`.
- Optional external image loaders are tied to tools and are disabled to keep this PR limited to libchafa.

## Conan recipe decisions

- Build libchafa only with:
  - `--without-tools`
  - `--without-avif --without-heif --without-jpeg --without-svg`
  - `--without-tiff --without-webp --without-jxl`
  - `--disable-gtk-doc --disable-man`
- Use `PkgConfigDeps` so upstream `PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.58)` resolves through Conan.
- Run upstream `make -j1 check` only when not cross-building; skip it for cross builds where target binaries cannot run on the build host.
- Add `test_package` that calls libchafa APIs directly: creates a canvas, draws RGB pixels, prints terminal text, and verifies non-empty output.

## HarmonyOS notes

- `config.guess` and `config.sub` are patched for `aarch64-unknown-linux-ohos`.
- `configure` is patched so generated `config.status` temporary directories use `${TMPDIR:-.}` and `umask 022`, matching the known HMDFS temp-directory workaround.
- The Automake test driver and libtool-generated test wrappers are patched to run through `$(SHELL)` because direct shebang execution is denied on the target runner.
- Native `make check` extends `LD_LIBRARY_PATH` with Conan dependency lib directories so test binaries can resolve `libglib-2.0.so.0`.
- Shared libraries are re-signed on native OHOS when `/data/service/hnp/bin/binary-sign-tool` is present; SDK/cross environments skip signing with a warning.

## Local validation completed

- Created isolated worktree from `origin/main` at commit `39cc707bbb72c47df1725ac99451a38a0539a074`.
- Downloaded official tarball and verified sha256.
- Confirmed official tarball contains generated `configure`.
- Confirmed upstream dependency and optional feature switches by inspecting `configure` / `configure.ac`.
- Conan build/test was not run locally because Conan is unavailable in this Windows environment.

## Device/shadow CI validation completed

- Device: `currentUser@10.62.189.79:2222`
- Isolated job: `/storage/Users/currentUser/ohos-users/currentUser/chafa-1.18.2-1924-20260807`
- Passing run: `currentUser-chafa-chafa-1.18.2-1924-20260807-conan-r11-20260807-174835-53993`
- Result: pass

- L0: pass, dependency availability and version collision checks passed.
- L1: pass, upstream `make check` and `test_package` executed; destructive negative test confirmed the test depends on chafa.
- L2: skip, no `bin/` directory because this package intentionally builds libchafa without command-line tools.
- L4: warning, `0001-config.guess.patch` is flagged by the generic dangerous-function scan due bundled upstream shell code in `config.guess`.
- L5: pass, library artifacts were packaged.

Re-run command used inside the isolated job:

```sh
JOB=$HOME/ohos-users/currentUser/chafa-1.18.2-1924-20260807
. $JOB/env.sh
cd $CI_REPO_ROOT
sh $HOME/bin/ohos-test-runner.sh --user "$OHOS_ISOLATED_USER" --lib chafa --task "$OHOS_ISOLATED_JOB-conan-r11" --mode heavy --try-lock --workdir "$CI_REPO_ROOT" -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```
