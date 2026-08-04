# dyld-headers 1378 Adaptation Notes

## Scope

The Homebrew formula is a header installation package. It copies the public
files from the upstream `include/` directory and does not build the Apple dyld
runtime. This adaptation preserves that scope.

## Source Verification

- Upstream tag: `dyld-1378`
- Archive SHA256: `509c8b081153a7b9ff08d6ddf0a681c0ab5190e1e336ef2e9748b801bdb9c59e`
- License: Apple Public Source License 2.0
- Packaged public files: 14

## Packaging

1. Download and verify the official GitHub tag archive.
2. Apply the declared patch set, which is empty for this version.
3. Copy the complete upstream `include/` tree into the Conan package.
4. Install `APPLE_LICENSE` under the package license directory.
5. Compile a C++17 consumer against the packaged headers.

## Validation

The consumer includes `mach-o/fixup-chains.h` and `objc-shared-cache.h`. These
headers expose portable data layouts and constants without requiring the Apple
Mach runtime. The test checks five compile-time invariants and two runtime data
access paths. Headers that expose Apple-only APIs remain packaged for source
compatibility but are not claimed to provide those APIs on OHOS.

The upstream project does contain a `dyld_tests` aggregate target. Its
`build-scripts/dyld_tests-build.sh` invokes `testing/build_ninja.py` and Apple
Xcode SDK tooling, while the official tag archive used by this recipe does not
contain the required `testing/` directory. It is therefore recorded in the
manifest but cannot be executed in this OHOS header-only adaptation.

The package contains no library or executable artifact. The Conan consumer test
is the applicable package validation and has seven assertions. Official
competition CI remains the final platform validation; HarmonyOS PC device
execution is not claimed.
