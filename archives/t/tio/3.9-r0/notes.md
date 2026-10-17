# tio 3.9-r0 Conan adaptation notes

## 最终状态
- 状态: built (conan create 验证通过, W3 本地 CI 模拟通过)
- 验证日期: 2026-09-18 (rebase 到最新 main 后本地全量 CI 流水线复验: L0/L1/L4/L5 全部通过)

## W0b — Historical experience verification
- Version 3.9 has a complete Conan recipe that was built and verified on a true OHOS aarch64 device.
- Version 3.9-r0 previously had only manifest.yaml and notes.md (manual build, no Conan recipe).
- This adaptation creates the Conan recipe for 3.9-r0, based on the proven 3.9 recipe.
- The "-r0" suffix follows Alpine Linux packaging convention; the upstream source is identical to v3.9.

## W0 — Dependency check
- Upstream Meson requires `threads`, `glib-2.0`, and one Lua pkg-config module from `lua-5.4`, `lua-5.3`, `lua-5.2`, `lua-5.1`, or `lua`.
- Repository-local dependency recipes exist for `glib/2.84.0.1` and `lua/5.4.8`; `lua/5.4.8` exports pkg-config name `lua-5.4`, matching tio's first Lua probe.
- Dependencies verified as published on the `ohpcd` conan remote.

## Source and build-system analysis
- Source: `https://github.com/tio/tio/releases/download/v3.9/tio-3.9.tar.xz`
- sha256: `06fe0c22e3e75274643c017928fbc85e86589bc1acd515d92f98eecd4bbab11b`
- Build system: Meson, C (`c_std=gnu99`), upstream version `3.9`.
- Meson probes optional termios2 and RS-485 support at configure time; RS-485 is only enabled when `host_machine.system() == 'linux'`, so OHOS falls back to the generic path.

## Recipe choices
- Keep Lua scripting enabled because upstream treats Lua as a required dependency.
- Use `PkgConfigDeps` so Meson resolves `glib-2.0` and `lua-5.4` from Conan dependencies.
- Disable optional man page and bash-completion installation with `install_man_pages=false` and `bashcompletiondir=no`.
- Package `bin/tio` and sign it on OHOS using `binary-sign-tool`/`llvm-objcopy` from `tools.build:compiler_executables` or the standard HNP paths.
- Meson archiver tools are injected into Conan's Meson native/cross files.

## Test package
- `test_package` runs hardware-independent smoke checks:
  - `tio --version` must print `tio 3.9` (upstream binary version, not the packaging version).
  - `tio --help` must include the usage banner.
  - `tio --list` exercises the serial-device/profile listing path without requiring an attached serial device.

## Version note
- The Conan version is `3.9-r0` (packaging version with Alpine-style revision suffix).
- The upstream binary reports version `3.9` (from the source tarball's embedded version).
- The test.sh checks for `tio 3.9` in the version output to match the actual binary behavior.
