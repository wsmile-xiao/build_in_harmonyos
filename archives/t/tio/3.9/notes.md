# tio 3.9 adaptation notes

## W0 dependency check
- Upstream Meson requires `threads`, `glib-2.0`, and one Lua pkg-config module from `lua-5.4`, `lua-5.3`, `lua-5.2`, `lua-5.1`, or `lua`.
- Repository-local dependency recipes exist for `glib/2.84.0.1` and `lua/5.4.8`; `lua/5.4.8` exports pkg-config name `lua-5.4`, matching tio's first Lua probe.
- Local Windows shell does not have a `conan` executable, so initial local `conan download ... -r=ohpcd --only-recipe` could not be executed.
- True-device W0 check passed in isolated `CONAN_HOME`: `glib/2.84.0.1` and `lua/5.4.8` recipes downloaded from `ohpcd`.

## Source and build-system analysis
- Source: `https://github.com/tio/tio/releases/download/v3.9/tio-3.9.tar.xz`
- sha256: `06fe0c22e3e75274643c017928fbc85e86589bc1acd515d92f98eecd4bbab11b`
- CI worker source-download mitigation: `conandata.yml` uses an ordered GitHub mirror list (`ghfast.top`, `gh-proxy.com`, `mirror.ghproxy.com`, `ghproxy.com`, `gitclone.com`, `kkgithub.com`) before the official GitHub URL. The sha256 is unchanged, so mirrors must serve byte-identical content.
- Build system: Meson, C (`c_std=gnu99`), upstream version `3.9`.
- Meson probes optional termios2 and RS-485 support at configure time; RS-485 is only enabled when `host_machine.system() == 'linux'`, so OHOS falls back to the generic path.
- Upstream has no `test()` targets in `meson.build`; hardware-facing serial connection tests are not suitable for local front-load validation.

## Recipe choices
- Keep Lua scripting enabled because upstream treats Lua as a required dependency.
- Use `PkgConfigDeps` so Meson resolves `glib-2.0` and `lua-5.4` from Conan dependencies.
- Disable optional man page and bash-completion installation with `install_man_pages=false` and `bashcompletiondir=no`.
- Package `bin/tio` and sign it on OHOS using `binary-sign-tool`/`llvm-objcopy` from `tools.build:compiler_executables` or the standard HNP paths.
- Meson archiver tools are injected into Conan's Meson native/cross files. If the profile only sets `clang`, the recipe derives `llvm-ar` and `llvm-ranlib` from the compiler directory.

## Test package
- `test_package` runs hardware-independent smoke checks:
  - `tio --version` must print `tio 3.9`.
  - `tio --help` must include the usage banner.
  - `tio --list` exercises the serial-device/profile listing path without requiring an attached serial device.

## Next verification commands

Local/shell preflight when Conan is available:

```sh
conan download "glib/2.84.0.1" -r=ohpcd --only-recipe
conan download "lua/5.4.8" -r=ohpcd --only-recipe
conan create archives/t/tio/3.9 --version=3.9
```

Single-package shadow CI / device queue command:

```sh
CI_PACKAGES="archives/t/tio/3.9" zsh ci/conan/build_and_test.sh
```

Shadow runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/t/tio/3.9
```

## True-device verification
- Device: `currentUser@10.62.189.79:2222`
- Run directory: `/storage/Users/currentUser/ohos-test-runs/tio-3.9-1892-manual-20260806-181517`
- Command:

```sh
CI_PACKAGES="archives/t/tio/3.9" zsh ci/conan/build_and_test.sh
```

- Result: pass.
- Summary: `Total: 1`, `Success: 1`, `Failed: 0`.
- Gates: `L0=pass`, `L1=pass`, `L4=pass`, `L5=pass`.
- `L2=skip` because the CI script's extra version/help smoke check reported a non-blocking warning; `test_package` itself executed `tio --version`, `tio --help`, and `tio --list` successfully under Conan run environment.

## Current status
- Built and verified on true OHOS aarch64 device.
- Shadow CI was not run, per request.
