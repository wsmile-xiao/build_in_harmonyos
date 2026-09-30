# starfetch 0.0.4 adaptation notes

## Build environment

- Build system: upstream makefile (single compile command; install target not
  used because it hardcodes /usr/local paths)
- Build date: 2026-09-28
- Compiler: `tools.build:compiler_executables:cxx` from the Conan profile,
  fallback `clang++`
- Status: built (local pre-validation)

## Issue

- Issue number: TO-BE-FILLED. No explicit issue number was found in the
  session context or project files for starfetch; per instruction the local
  pre-adaptation proceeds first and the issue is marked as pending.

## W0 dependency conclusion

- Runtime dependencies: none (nlohmann/json is vendored as a single header).
- Build dependencies: a C++17 compiler only.
- Test dependencies: none (upstream ships no test suite).
- Missing dependencies: none.
- Split dependency adaptation needed: no.
- Blockers: none.

## Source audit

- Upstream repository: https://github.com/Haruno19/starfetch
- Tag: `0.0.4` (tree `02528fda298ef5d2aae25027513fa541017f235c`)
- Source URL:
  https://github.com/Haruno19/starfetch/archive/refs/tags/0.0.4.tar.gz
- Source SHA256:
  `a95cff9ee6f2306211389a79a7016ae9607fafe53b0f717f0962c70cec1269bb`
- Archive format: tar.gz (explicit `filename=` passed so the Conan downloader
  always detects the format, per the xmodem `BadZipFile` lesson)
- Contains tests: no — upstream ships no test directory.
- License: GPL-3.0 (35149-byte LICENSE file).

## Build system analysis

- `makefile` `all`/`starfetch` target compiles `src/starfetch.cpp` with
  `-std=c++17`; the recipe reproduces that single command with the Conan
  profile compiler.
- `make install` uses `rm -rf`, `mkdir`, `cp`, `chmod`, `ln -s` against
  `/usr/local/share` and `/usr/local/bin`; not usable for Conan packaging, so
  `package()` copies `bin/starfetch` plus `res/*` data instead.
- The GUI/ subdirectory is a separate Qt project and is not part of the CLI;
  it is not built.

## Patch

- `patches/0001-runtime-resource-dir.patch`
  - Reason: the source hardcodes `path = "/usr/local/share/starfetch/"`,
    which does not exist on OHOS and breaks relocatable Conan packages.
  - Change: when the `STARFETCH_RES_DIR` environment variable is set, it is
    used as the resource directory (trailing slashes normalized); otherwise
    the upstream default is kept, so upstream behavior on a normal Linux
    install is unchanged.
  - Platforms affected: all non-Windows; Windows branch untouched.
  - `package_info()` exports `STARFETCH_RES_DIR` and `PATH` through
    `runenv_info`, so consumers (and test_package) work without extra setup.

## Upstream test inventory

- Unit tests: 0 (none shipped).
- Integration tests: 0.
- Total collected: 0.
- Degradation: since no upstream suite exists, verification relies on the
  19-assertion consumer test in `test_package` (binary discovery via PATH,
  resource packaging, `-h`, `-l`, `-n orion`, unknown-name error path,
  `-c red` color codes, random mode).

## Test evidence

- Local (Windows host): source archive SHA256 verified; patch applies
  cleanly against the pristine tag archive (`git apply --check`); Python
  syntax checks passed; YAML structure checks passed; OHOS aarch64
  cross-compile smoke test passed (DevEco clang++ 15.0.4, ELF64 AArch64).
- Local static gates: `lang-preflight` PASS (cpp=cpp); `conan-verify` G1 PASS
  after moving sources/patches into `conandata.yml`; G2+ requires the OHOS
  toolchain and is deferred to the device.
- Device shadow CI r1 (`starfetch-0.0.4-20260929`, 2026-09-29):
  - G0/G0e/L0 pass (no version collision, commands.json valid, directory
    structure valid).
  - KC failed: `ci/conan/build_and_test.sh:980: permission denied: bash` —
    the isolated job `env.sh` did not include `/data/service/hnp/bin` in
    PATH (the reference job env did). Root cause: environment, not recipe.
  - Fix: prepend `/data/service/hnp/bin` to PATH in the job's `env.sh`;
    rerun as r2.
- Device shadow CI r2 (`starfetch-0.0.4-20260929`, 2026-09-29, run dir
  `codex-0.0.4-starfetch-0.0.4-20260929-conan-20260929-120547-25200`,
  lock wait 0s):
  - `L0_RESULT=pass`, `L1_RESULT=pass` (test_package executed),
    `L2_RESULT=pass` (smoke OK), `L4_RESULT=pass`, `L5_RESULT=pass`;
    build summary 100% (1/1); exit code 0.
  - L1e destructive negative test confirmed: the consumer test genuinely
    depends on the package artifacts.
  - Consumer test: `19/19 assertions passed` on device (the initial draft
    undercounted them as 12; all files now record 19).
  - Package: `starfetch/0.0.4` package id
    `6b129b068851896169fae42d399fa922d239ce8a`.
- HarmonyOS PC device execution: done (r2, all gates pass).
- Competition CI: not run yet.

## Dependencies

- Runtime dependencies: none.
- Conan package dependencies: none.
- Build dependency: C++17 compiler (clang++ from the OHOS toolchain on CI).

## Next steps

1. Fill in the issue number once it is created/confirmed.
2. On-device shadow CI is complete (r2, all gates pass, see Test evidence).
3. Open the PR against `feat/starfetch-0.0.4-codex` with the evidence
   recorded above.
