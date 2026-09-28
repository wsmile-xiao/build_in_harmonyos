# ud 1.1.0 HarmonyOS PC verification

- Board: `@tank_you` claimed exact task `ud/1.1.0`, branch
  `feat/ud-1.1.0`, in the 10-fire-seed activity. The board labels it C++;
  the upstream program is one C source file.
- Official upstream tag: `https://github.com/xyproto/ud/releases/tag/v1.1.0`.
  Tag archive `https://github.com/xyproto/ud/archive/refs/tags/v1.1.0.tar.gz`,
  3818 bytes, SHA-256
  `994459ac0b69db6fab913e1f38f92cb02fef26693cdcf15bcd28899010ff5f2f`.
  The identical archive was copied to the target and verified there.
- Native work directory:
  `/data/storage/el2/base/haps/entry/files/ud-1.1.0-work`.
  Unmodified `main.c` compiles and its basic conversions work with target
  Clang 15 when `TMPDIR` points to the private writable directory.
- The unmodified upstream CMake project, even configured with
  `-DCMAKE_C_COMPILER=clang`, builds with `gcc` because its `CMakeLists.txt`
  overrides the compiler **after** `project(ud)`. The target has no `gcc`,
  so `cmake --build` fails with `gcc: No such file or directory`.
  Removing that override exposed another defect: the file's
  `set(TARGET ud PROPERTY C_STANDARD 18)` does not set a target property;
  CMake `C_STANDARD=18` is also unsupported on this target. The recipe uses
  `set(CMAKE_C_STANDARD 17)` (C17/C18 name the same 2018 ISO revision).
  The C program source and its outputs are not changed.
- The upstream CMake file declares no CTest cases. Its GitHub workflow runs
  `ctest` with no registered tests and invokes `./ud` once without an output
  assertion. The adaptation adds nine deterministic installed-package checks:
  seven exact conversion/version outputs, help, and invalid-input rejection.
- Final native isolated `conan create -pr:h ohos-aarch64 -pr:b ohos-aarch64`
  passed; consumer checks 9/9. Log `create-v5-local-source.log` SHA-256:
  `3f6d57e7e1968ef2faebae778e28048beb5a7b32ef47c813b5eabb24b36b9e49`.
  Recipe revision `9dac21f4c6b5ed68ba9df06a5f7fde41`, package revision
  `282671767efd557c11f6b804e65e399e`. The installed executable is an
  arm64 musl ELF with executable mode 0755; the BSD-3-Clause license is
  packaged alongside it.
- The target could not download the official GitHub archive during Conan
  source acquisition (HTTPS connect timeout). Only the validation copy of
  `conandata.yml` used a local `file://` URL to the same hash-verified bytes.
  The submitted `conandata.yml` retains the official HTTPS URL. This does
  not verify target network reliability or cross-user package installation.
