# DRAFT-coinutils-autotools-dual-config-guess

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

COIN-OR CoinUtils 2.11.12 is a generated autotools release archive with more than
one platform-probing layer:

- `config.guess` at the source root
- `CoinUtils/config.guess` under the component subdirectory
- matching root and nested `configure` scripts

On HarmonyOS PC, the target can report platform strings such as `HarmonyOS` or
`HongMeng`. Old generated `config.guess` scripts do not classify those strings,
so a naive one-file patch can leave another configure layer unhandled.

## Root Cause

COIN-OR releases preserve generated autotools files. CoinUtils does not rely on a
single central platform detector during the whole build: the top-level project
and the nested component both ship their own generated scripts. Each copy has its
own version-specific context and must be patched or otherwise verified.

For OHOS, the useful mapping is to treat HarmonyOS/HongMeng as Linux-like with
musl-compatible libc semantics for the package triplet used by the Conan profile.
The 2.11.12 adaptation therefore patches both copies and maps aarch64 to a
Linux/OHOS style result instead of changing global build settings outside the
package.

## Recommended Handling

Inventory generated platform probes before writing the patch:

```bash
find . -name config.guess -o -name configure
```

For CoinUtils 2.11.12, keep both patches in the version directory:

- `patches/0002-coinutils-config-guess.patch`
- `patches/0003-root-config-guess.patch`

Validate patch applicability against the exact release tarball, not a newer
COIN-OR branch:

```bash
git apply --check patches/0002-coinutils-config-guess.patch
git apply --check patches/0003-root-config-guess.patch
```

## Evidence

The 2.11.12 package passed shadow CI on the OpenHarmony PC worker:

```text
run_root=/storage/Users/currentUser/ohpc-ci-shadow/runs/manual-coinutils-2.11.12-min-20260908T025816Z-22719
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L4_RESULT=pass: patches clean
```

## Reuse Boundary

This draft is most useful for nested autotools source releases. It should not be
used to justify broad toolchain changes, CMake platform overrides, or claiming
that all COIN-OR packages have the exact same patch context. Each version still
needs a source inventory and `git apply --check`.
