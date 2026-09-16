# HarmonyOS device validation: gcc-ada 9.5.0

- Issue: #2281
- Date: 2026-08-22
- Device: `currentUser@10.62.221.191:2222`
- Branch: `feat/gcc-ada-9.5.0`
- SDK: `26.0.0.18`

## Result

The targeted native build, install, and package consumer workflow passed on a
real AArch64 HarmonyOS device.

- r70 produced the reusable native GCC/Ada build cache.
- r120 completed `all-target-libada`.
- r121 completed `make -C gcc selftest`.
- r128 built and signed the required GNAT tools with
  `GNATTOOLS_DIAGNOSTIC=pass`.
- r129 installed GCC, GNAT drivers, `gnat1`, libgcc, libgnat/libgnarl, Ada
  sources, objects, and ALI files with `GCC_ADA_INSTALL_DIAGNOSTIC=pass`.
- r143 proved the exception-unwind fix: the default GCC unwinder timed out
  after printing `exception:before`, while the same program linked with the
  OHOS SDK `libunwind.a` exited `0` and emitted
  `ADA_UNWIND_DIAGNOSTIC=pass`.
- r144 used the relocatable signed native `gcc` proxy and automatic link-only
  SDK libunwind injection. The unmodified six-check Ada consumer exited `0`
  and printed `gcc-ada checks passed: 6`.

The persisted final run is:

```text
/storage/Users/currentUser/ohos-users/codex/gcc-ada-9.5.0-2281/targeted/r144/currentUser-gcc-ada-full-package-r144-20260822-093702-38510
```

Its result contract is:

```text
full_package_exit_code=0
gcc-ada checks passed: 6
GCC_ADA_FULL_PACKAGE_DIAGNOSTIC=pass
```

## Coverage

The final consumer compiled, bound, linked, signed, and ran Ada code covering:

- integer and string runtime operations;
- generic containers;
- exception raise and catch through the SDK unwinder;
- task rendezvous;
- protected-object locking.

The r144 compile-only trace contained no libunwind injection, while its link
map resolved the SDK AArch64 `libunwind.a`. The installed `libgnarl.a` had no
undefined references to the two unsupported Linux pthread attribute APIs.

## Remaining gate

These runs reused the persisted r70 build tree and applied fixes at their
owning phases. A clean shadow CI invocation from the final recipe remains the
release gate:

```sh
CI_PACKAGES="archives/g/gcc-ada/9.5.0" zsh ci/conan/build_and_test.sh
```

Run it only in an assigned heavy-device window while holding the global lock.
