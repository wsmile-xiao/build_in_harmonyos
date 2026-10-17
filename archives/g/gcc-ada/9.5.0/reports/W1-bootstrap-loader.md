# W1 bootstrap loader record: gcc-ada 9.5.0

- Issue: #2281
- Date: 2026-08-21
- Branch: feat/gcc-ada-9.5.0
- Worktree: D:\harmonyos\worktrees\gcc-ada

## Implemented

The build-only Alpine GNAT seed now uses a signed OHOS XPM-compatible musl
loader before any seed executable is started.

- Official musl 1.1.24 source and SHA256 are recorded in conandata.yml.
- musl-ohos-xpm-loader.patch keeps the initial file mapping read-only, copies
  writable PT_LOAD data into anonymous mappings, and remaps the lowest
  executable LOAD with normal fixed mapping.
- build_ohos_loader.sh builds the loader with the device clang/make toolchain.
- prepare_ohos_bootstrap.py patches seed ELF interpreters to
  /proc/self/fd/9 and maps the five tested shared dependencies to short names.
- The generated Python launcher supplies fd 9, LD_LIBRARY_PATH and
  GCC_EXEC_PREFIX without LD_PRELOAD.
- GNATMAKE, GNATBIND and GNATLINK now point at the loader wrappers.

## Verification

- python -m py_compile on conanfile.py and prepare_ohos_bootstrap.py: pass.
- Official musl 1.1.24 patch application check: pass.
- git diff --check: pass.
- Existing device preflight remains pass:
  seed_probe.o and SHORT_NEEDED_DIAGNOSTIC=pass from r53.
- Full Conan create/package/test: not run after W1 recipe changes.

## Blocker

The HarmonyOS device currentUser@10.62.222.172:2222 was unreachable during
the retry window (SSH connection timeout). Therefore no claim is made for the
new recipe's full Conan build, package install, consumer test, or shadow CI.
Resume with the global device lock check and run one targeted
archives/g/gcc-ada/9.5.0 package when SSH is available.
