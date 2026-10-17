# Link-only OHOS SDK libunwind integration for GCC Ada 9

## Scope

This draft applies to the GCC Ada 9.5.0 HarmonyOS package from issue #2281.
It addresses a runtime defect that is invisible to compiler version checks and
compile-only probes.

## Failure signature

The GCC 9 Ada runtime and application built successfully, but an exception
test stopped after its pre-raise marker and did not exit:

```text
exception:before
<timeout>
```

This is distinct from a missing `_Unwind_*` symbol: the executable links, but
GCC 9's `unwind-dw2` does not complete propagation on this platform.

## A/B result

The same Ada source was linked twice on the HarmonyOS device:

- default GCC 9 unwinder: timed out after `exception:before`;
- OHOS SDK AArch64 `libunwind.a`: exited 0 and emitted
  `ADA_UNWIND_DIAGNOSTIC=pass`.

The final consumer subsequently passed strings, containers, exception
handling, task rendezvous, and protected-object locking.

## Package contract

The installed native GCC proxy distinguishes compilation from linking:

1. `-c`, `-S`, `-E`, dependency generation, and `-fsyntax-only` disable link
   injection.
2. A link must also contain a real input, avoiding bare query invocations.
3. The driver derives the SDK native root from the active sysroot.
4. It requires `llvm/lib/aarch64-linux-ohos/libunwind.a` to exist.
5. The archive is injected only for the link under `--whole-archive` and
   `--no-whole-archive` so the needed unwind implementation is retained.

## Verification

- Compile-only trace: no SDK libunwind injection.
- Link map: resolves the OHOS SDK AArch64 `libunwind.a`.
- Device r143: A/B diagnostic reproduced the default hang and passed the SDK
  variant.
- Device r144: packaged consumer exited 0 with
  `gcc-ada checks passed: 6`.
- Clean CI #31486: complete package and consumer test passed.

## Non-solutions

- Adding linker archives to CFLAGS or all GCC invocations.
- Disabling Ada exceptions or replacing `_Unwind_*` with stubs.
- Silently omitting libunwind when the SDK path is missing.
- Treating successful compilation as proof that exception propagation works.
