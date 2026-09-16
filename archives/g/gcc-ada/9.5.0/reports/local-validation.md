# Local validation: gcc-ada 9.5.0

Date: 2026-08-26

## Passed

- Official GCC 9.5.0 archive SHA256 verified as
  `27769f64ef1d4cd5e2be8682c0c93f9887983e6cfd1a927ce5a0a2915a95cf8f`.
- Alpine `APKINDEX.tar.gz` downloaded from `v3.12/main/aarch64` and package
  metadata checked for GCC/GNAT 9.3 plus all `gnat1` SONAME providers.
- Nine official APK downloads SHA256-verified; values are pinned in
  `conandata.yml`.
- `.PKGINFO` confirms `gcc-gnat` provides `gnat`, `gnatmake`, `gnatbind`,
  `gnatlink`, and `gcc-gnat-bootstrap`.
- Local ELF64 parser confirmed AArch64/musl interpreter and exact shared
  library dependencies for seed executables.
- The recipe's own APKv2 extractor processed all nine packages, recorded 31
  distribution links, and produced all 11 required seed artifacts.
- Python bytecode/AST parsing passed for the main recipe and test recipe.
- Conan 2.29.1 `inspect` passed and loaded all source/bootstrap metadata.
- YAML parsing passed for `conandata.yml`, `manifest.yaml`, and test
  `MANIFEST.yml`; the declared assertion count is 17 after adding ten
  executable upstream tests.
- The 12 imported upstream test/support files match the checksum-verified GCC
  9.5.0 archive byte for byte.
- Both gcc-ada knowledge drafts passed required-field and repository knowledge
  quality checks (`KC_RESULT=pass`, zero errors).

## Clean shadow CI passed

- Clean CI #31486 completed the full source build, package installation,
  consumer execution, L0 and L1 on commit `2da8d6c871`.
- `conan-build-test` completed in 55 minutes 21 seconds.
- The follow-up run must additionally emit
  `UPSTREAM_ADA_SUBSET_TOTAL=10/10` for the reviewer-requested upstream subset.

## Device preflight passed

- The signed Alpine GNAT seed compiled `seed_probe.adb` on the authorized
  AArch64 HarmonyOS device.
- Run `currentUser-gcc-ada-xpm-loader-ada-r53-2281-20260820-235528-61246`
  exited `0` and emitted `SHORT_NEEDED_DIAGNOSTIC=pass`.
- The resulting `seed_probe.o` is an AArch64 relocatable ELF. See
  `reports/device-preflight-r53.md` for the loader and dependency details.

## Not run on the Windows host

- The Windows host cannot execute AArch64/musl GNAT binaries.
- No WSL distribution or native GNAT is installed.
- No `conan create` was attempted because this compiler recipe intentionally
  validates only OHOS/armv8.
- The newly added 10-case upstream subset cannot run on Windows because its
  compiler and test executables target native OHOS/AArch64.

## Next device commands

```sh
python3 scripts/ohc-run.py conan-verify gcc-ada 9.5.0
CI_PACKAGES="archives/g/gcc-ada/9.5.0" zsh ci/conan/build_and_test.sh
```

The first failing log should be classified before patching: seed execution,
seed compile/sysroot, GCC configure, `all-gcc`, libgcc, libada, install, or
consumer tasking execution.
