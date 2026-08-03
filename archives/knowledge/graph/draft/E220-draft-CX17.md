# E220 draft - Select an OHOS-compatible OpenSSL entropy source

> **Contributor**: chenicia | **Status**: VERIFIED DRAFT | **Updated**: 2026-07-25
> **Severity**: high | **Category**: OpenSSL / entropy / OHOS SDK

## Usage

Use this entry when an OHOS link against static OpenSSL fails on `__fd_chk`,
especially when the diagnostic names `rand_unix.c` or
`libdefault-lib-rand_unix.o`. The method applies before adding any compatibility
symbol: first determine which OpenSSL entropy branch introduced the reference.

## Scope

- OpenSSL 3.x built with a Linux-family Perl `Configure` target.
- OHOS armv8 static `libcrypto.a`, commonly linked into a shared downstream
  library such as libcurl.
- SDKs where the archive can reference `__fd_chk` but target libraries do not
  export it.

Do not use this configuration on a target that lacks a working `getrandom`
system call. Such a target needs a documented and audited public entropy API.

## Inputs

- The failing linker diagnostic and the exact `libcrypto.a` used downstream.
- SDK `llvm-nm`, `llvm-ar`, `llvm-objdump`, and `llvm-readelf` tools.
- OpenSSL source, including `providers/implementations/rands/seeding/rand_unix.c`.
- A consumer that calls `RAND_bytes`.

## Outputs

- OpenSSL is configured with `--with-rand-seed=getrandom`.
- The `DEVRANDOM_WAIT` and `FD_SET` fallback is not compiled into
  `rand_unix.o`.
- `libcrypto.a` has no unresolved `__fd_chk`.
- A real RAND consumer cross-compiles and links for AArch64 OHOS.

## Symptom And Root Cause

The failure normally appears only in a downstream shared link:

```text
ld.lld: error: undefined symbol: __fd_chk
>>> referenced by rand_unix.c
>>> libdefault-lib-rand_unix.o:(ossl_pool_acquire_entropy) in libcrypto.a
```

OpenSSL's default `--with-rand-seed=os` enables both `getrandom` and
`devrandom`. On Linux-family targets, `DEVRANDOM_WAIT` adds a readiness fallback
that checks a descriptor against `FD_SETSIZE`, clears an `fd_set`, and invokes
`FD_SET`. The OHOS toolchain lowers that operation to `__fd_chk`, while the
target SDK libraries do not provide the private helper.

The defect can remain hidden because static archives are lazy-linked. Hashing
and `SSL_CTX_new` consumers may not pull the random backend object. A consumer
must call `RAND_bytes` to make this link boundary observable.

## Implementation

Select the public kernel entropy source explicitly:

```text
perl ./Configure linux-aarch64 \
  --with-rand-seed=getrandom \
  no-asm no-shared -fPIC
make -j1 build_sw build_tests
```

For Conan cross-builds, derive `--target=aarch64-linux-ohos`, the SDK sysroot,
and `llvm-ar`/`llvm-ranlib`/`llvm-nm` from
`tools.build:compiler_executables`. Do not hardcode a user-specific SDK path.

`getrandom` remains the cryptographic entropy source. This is not equivalent to
`--with-rand-seed=none`, which disables automatic seeding and is unsafe for key
generation and related operations.

## Forbidden Approaches

- Do not define or link a private `__fd_chk` shim.
- Do not use `--with-rand-seed=none` to make the symbol disappear.
- Do not remove random seeding code with an ad hoc source patch.
- Do not validate only SHA or SSL initialization APIs; call `RAND_bytes`.
- Do not report target runtime success when only cross-compilation and linking
  were performed.

## Verification

1. Confirm the old archive contains the defect:

   ```text
   llvm-nm -u libcrypto.a | rg __fd_chk
   ```

2. Force a clean OpenSSL source build with the new seed selection.
3. Require the same `llvm-nm` command to return no `__fd_chk` reference.
4. Link an AArch64 consumer that calls `RAND_bytes`, `SHA256`, and
   `SSL_CTX_new`.
5. Compile all upstream test programs and run `make test` when `can_run=true`.
6. Inspect the consumer with `llvm-readelf -h` and require AArch64 ELF.
7. On a HarmonyOS target, run the consumer and require `openssl version -a`
   to report `/ssl`, `/lib/engines-3`, and `/lib/ossl-modules` exactly.

When `can_run=false`, steps 2-4 prove build and link compatibility only. Runtime
entropy behavior still requires a HarmonyOS target.

## Validated Example

OpenSSL 3.5.6.1 is the first validation target. The original curl 8.15.0 link
failure and object disassembly establish the negative case. A forced OHOS
`conan create` then passed at recipe revision
`8717e485e00723b4b2fece557d5623fd` and package revision
`e5e3fe1944e9ce718ed1a8f8ac5efeee`; the build log SHA256 is
`F08A9EA67021D45850D3893DCB691628A0A8B173D5FBD9679C044802AA039DFE`.

The resulting package contains 149 files and two static archives, with no
OpenSSL shared objects. `llvm-nm -u` found zero `__fd_chk` references in both
`libcrypto.a` and the packaged CLI. A consumer calling `RAND_bytes`, SHA-256,
and `SSL_CTX_new` linked as ELF64 AArch64. All upstream test programs also
compiled and linked. Conan reported `can_run=false` on the Windows host, so the
final CLI and C consumer were transferred to a HarmonyOS HongMeng Kernel 1.12.0
aarch64 device, checked by SHA256, signed in their final HMDFS paths, and run.
The C API checks passed 4/4 and CLI checks passed 6/6, including exact path,
fixed SHA-256, and random-generation assertions.

## Related Knowledge

- E006: disable problematic OpenSSL AArch64 assembly with `no-asm`.
