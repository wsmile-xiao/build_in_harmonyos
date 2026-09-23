# ncmpc 0.53 HarmonyOS PC pre-adaptation notes

## Status

- Conan recipe and consumer test prepared.
- 2026-09-12 local recheck passed the W0 dependency preflight, source SHA256
  verification, Python/YAML parsing, Conan inspection, recipe export, and
  Conan `patch_ng` application of all four OHOS patches.
- The Windows host cannot run a native HarmonyOS arm64 `conan create`: the
  available Conan 2.29.1 installation has no custom `OHOS` setting, and no
  local HarmonyOS Meson/Ninja SDK is available.
- The first true-device shadow CI run on 2026-09-12 reached compilation,
  upstream testing, and packaging, then failed in the consumer test because
  the installed ELF copy was rejected by the device. A rerun with the
  package-directory remirror fix passed all required CI levels.
- Issue tracking is omitted because the request states that the issue is no longer used.

## Upstream source

- URL: https://www.musicpd.org/download/ncmpc/0/ncmpc-0.53.tar.xz
- SHA256: `92c68bb9bf294d48209587b19df9005db7247e9c38d7e4fb74f8586e6f23c56f`
- Build system: Meson
- Language standard: C++23

## Dependency audit

Required Conan packages:

- `fmt/12.2.0`
- `libmpdclient/2.23`
- `ncurses/6.6`

Build tools:

- `meson/1.11.0`
- `ninja/1.12.1`

Optional upstream features disabled for the minimal package:

- PCRE2 regular expressions
- LIRC remote control
- gettext/NLS
- iconv
- Sphinx documentation and manual generation

No dependency adaptation was added to this ncmpc change.

## Source and test analysis

The release archive includes the complete Meson project and the `test/`
directory. `test/meson.build` builds `run_hscroll`, but does not register a
`test()` entry. The recipe therefore runs `meson test` for the upstream test
hook and explicitly executes `run_hscroll hello '|' 5 3` when the target can
run. This keeps the test evidence honest while still exercising the shipped
upstream test program.

The consumer test runs the installed `ncmpc --version` command and checks:

1. The packaged command is discoverable through `package_info()` and
   `VirtualRunEnv`.
2. The output reports `ncmpc version: 0.53`.
3. Wide-character curses support is enabled.

## HarmonyOS considerations

- The package is an application and exports `bin` so the consumer test can
  locate `ncmpc`.
- `MesonToolchain` is configured with `wrap_mode=nodownload`; all build
  dependencies come from Conan.
- The recipe injects absolute `ar`, `ranlib`, and `pkg-config` paths into
  generated Meson machine files when the OHOS worker does not expose them in
  the recipe environment.
- The device profile declares C++17, but ncmpc 0.53 uses `std::span` and
  upstream declares C++23. The recipe fixes the package build to C++20,
  which is accepted by the worker's clang 15 and covers the required API.
- The OHOS source patch removes `constexpr` from runtime-only address-span
  accessors and supplies a chrono comparator based on `<`/`>` because the
  worker's libc++ 15 does not provide the upstream `time_point <=>` path.
- No binary signing command is added locally; linker-signed OHOS artifacts
  should be checked by shadow CI according to the repository workflow.
- Shadow CI on 2026-09-12 reached compilation, upstream `run_hscroll`, and
  packaging. Its first test-package attempt failed because `meson install`
  produced a package copy of `bin/ncmpc` that the device rejected with
  `Operation not permitted`, even though the build-tree ELF ran successfully.
  The recipe now re-mirrors the linker-produced build ELF into
  `package/bin/ncmpc` on OHOS and restores mode `0755`.

## Local validation

```powershell
git diff --check
python -m py_compile archives/n/ncmpc/0.53/conanfile.py archives/n/ncmpc/0.53/test_package/conanfile.py
conan inspect archives/n/ncmpc/0.53/conanfile.py
```

Completed locally:

- `python -m py_compile`: passed for both Conan files.
- YAML parsing: passed for `conandata.yml`, `manifest.yaml`, and
  `test_package/MANIFEST.yml`.
- `git diff --check` on tracked files: passed. The untracked patch file keeps
  source tabs in its unified-diff context.
- W0 direct dependency preflight: passed for `fmt/12.2.0`,
  `libmpdclient/2.23`, `ncurses/6.6`, `meson/1.11.0`, and `ninja/1.12.1`;
  all five are published in ohpcd.
- Conan graph resolution with a Linux/POSIX override: passed; the graph
  resolves ncmpc, fmt, libmpdclient, ncurses, Meson, Ninja, and Meson's zlib
  build dependency. The synthetic profile has no matching package binaries,
  so this is dependency-graph evidence rather than a build result.
- `conan inspect`: passed.
- `conan export`: passed for `ncmpc/0.53`; the recipe exported all four
  patches and `conandata.yml`.
- Fresh-source Conan `patch_ng` application: passed for all four OHOS patches.
- Archive SHA256: passed and matches `conandata.yml` and `manifest.yaml`.

The current Windows Conan 2.29.1 installation does not include the custom
`OHOS` settings enum, and the host does not provide a local Meson/Ninja
HarmonyOS toolchain. Therefore a native HarmonyOS arm64 `conan create` and
the consumer executable test are not claimed in this round.

## Shadow CI attempts

- 2026-09-12 rerun job base:
  `/storage/Users/currentUser/ohos-users/codex/ncmpc-0.53-shadow-20260912`
- Rerun 1:
  `codex-ncmpc-ncmpc-0.53-shadow-20260912-conan-20260912-015033-40718`
  compiled and packaged successfully, but test package execution failed with
  `Operation not permitted` because the `meson install` copy of `bin/ncmpc`
  was not accepted by the device.
- Rerun 2:
  `codex-ncmpc-ncmpc-0.53-shadow-20260912-r2-conan-20260912-015851-43675`
  passed the complete single-package pipeline. The build compiled 115/115
  targets, executed `run_hscroll`, packaged `bin/ncmpc`, and the consumer
  test reported version `0.53` with `wide` support.
- Rerun 2 metadata reported:
  `L0=pass`, `L1=pass`, `L2=pass`, `L4=pass`, and `L5=pass`.

## Knowledge drafts

- `knowledge/drafts/DRAFT-ncmpc-meson-install-elf-remirror.md` and `.kv`
  capture the package-stage executable failure where the Meson build-tree ELF
  runs but the installed Conan package copy exits 126 on OHOS. This is the
  reusable packaging/runtime piece that justified the final remirror fix.
- `knowledge/drafts/DRAFT-ncmpc-libcpp15-cxx20-compat.md` and `.kv` capture the
  C++20/OHOS libc++ 15 compatibility pattern: keep the standard override local
  to the package recipe, then patch the narrow `constexpr std::span` and chrono
  comparator failures without platform macros.
- These drafts intentionally omit device IPs, private keys, generated
  `ci-metadata.json`, and full remote workspace paths. They are directly tied
  to `ncmpc 0.53` and support a B-class difficulty application because the
  successful adaptation required compile-time, packaging-time, and runtime
  diagnosis on a true HarmonyOS device.

- Job base:
  `/storage/Users/currentUser/ohos-users/codex/ncmpc-0.53-shadow-20260911`
- Run 1:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-100711-10173`
  stopped before compilation because the isolated Conan home had no ohpcd
  remote and could not resolve `libmpdclient/2.23`.
- Run 2:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-101201-11608`
  resolved all dependencies and downloaded the source, then stopped because
  direct execution of the Meson shell wrapper returned `Permission denied`
  on HMDFS. The recipe now invokes that wrapper through the configured shell.
- Run 3:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-101900-14314`
  used the shell-wrapper fix but Meson could not find `pkg-config` in its
  cross/native machine file. The recipe now injects the worker's absolute
  `pkg-config` path.
- Run 4:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-102530-18205`
  passed Meson configuration and started compilation, then failed because
  the device profile forced `-std=c++17`; ncmpc's `std::span` declarations
  require C++20 or newer. The recipe now overrides the build standard to
  C++20.
- Run 5:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-103136-29274`
  compiled with C++20 but exposed two OHOS libc++ 15 compatibility issues:
  `constexpr` address-span accessors rejected `reinterpret_cast`, and the
  default `std::compare_three_way` could not compare chrono time points. The
  recipe now applies a minimal OHOS-only source patch for both cases.
- Run 6:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-110246-12164`
  stopped in `source()` because Conan forbids accessing `self.settings` from
  that method. Patch application was moved to `build()`.
- Run 7:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-114644-2766`
  reached compilation but the timer patch inserted its comparator inside the
  tree template argument. The hunk was corrected to define the comparator
  before the tree member.
- Run 8:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-115937-27132`
  stopped because the timer patch hunk header under-reported its new line
  count. The hunk was corrected from 14 to 18 new lines.
- Run 9:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-124256-19463`
  compiled and packaged the application, but the test package selected
  `bash` by name; the isolated test environment did not expose that name.
  The test recipe now uses the absolute HNP bash path when available.
- Run 10:
  `codex-0.53-ncmpc-0.53-shadow-20260911-conan-20260911-124900-31019`
  contains the corrected test recipe and remains queued on the device. At
  handoff, an external qtdeclarative heavy runner still holds the global
  device lock, so this run has no exit code yet.

## Next step

```sh
python scripts/ohc/pre_pr_audit.py archives/n/ncmpc/0.53
```

Shadow CI is complete. Generated device reports and device-sensitive paths
remain outside this PR; the local branch still needs the repository submission
audit and one final commit/PR.
