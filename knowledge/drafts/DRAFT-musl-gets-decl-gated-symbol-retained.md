# Draft: OHOS musl keeps the gets symbol, only the declaration is C11-gated

> Source event: blimps/3.9 path-update audit, 2026-09-05. B-1 was first drafted
> as "musl removed gets() -> build failure", CHALLENGED by Auditor probes, then
> independently reproduced and rewritten by the Curator on OHOS facts.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Legacy C code (pre-C11, K&R era) calls `gets()` in interactive prompt paths —
blimps 3.9 has 129 call sites. On OHOS the natural assumption is "musl removed
gets(), so the build must fail" (the E093 genus). That assumption is wrong.

## Measured facts (OHOS device, double probe)

1. Symbol side: the runtime loader exports a real, distinct `gets` symbol:

```text
/data/service/hnp/bin/llvm-nm -D /lib/ld-musl-aarch64.so.1 | grep -wE "gets|fgets|getline"
# T fgets   0x1c18e8
# T getline 0x1c54b8
# T gets    0x1c54c4
```

2. Declaration side: the sysroot `stdio.h` gates **only the declaration**:

```c
#if __STDC_VERSION__ < 201112L
gets(...)
#endif
```

Under the default gnu17 mode (`__STDC_VERSION__ == 201710`) the declaration is
hidden, so `gets(buf)` compiles with only a
`-Wimplicit-function-declaration` **warning**, links against the exported
symbol, and runs correctly (probe: `printf ... | clang -xc - -o probe && echo
ok | ./probe` → exit 0). In a pristine-tree compile of blimps' motifj.c (12
gets call sites) with no macro and no -Wno-error: exit 0, 77 warnings
(68 deprecated-non-prototype + 9 implicit-function-declaration), 0 errors.

## Reverse genus vs E093

- E093: musl does not implement a function → undefined reference → build
  failure.
- This entry: symbol retained + declaration hidden → warning-only → builds and
  runs.

Do not merge the two; diagnose by probing both sides (symbol table + a
no-flag compile) before writing the root cause down.

## Recommended approach (hardening, not a fix)

One preprocessor define on the make command line covers every call site with
zero source changes:

```bash
make ... DEFINES="-D'gets(s)=fgets(s,8192,stdin)'"     # protomat: same define inside CFLAGS
```

Honest tradeoff: this changes behavior from an unbounded read to an 8KB
bounded read. That is hardening / technical-debt retirement — not a repair of
a build failure — and the semantic change must be declared in the package
notes/README (as done in blimps 3.9).

## Fallbacks

1. Keep as-is and accept the warnings — fully legal, faithful to upstream
   semantics, build unaffected.
2. Per-call-site fgets rewrites (Debian-style gets.patch/more_gets.patch,
   ~53KB for blimps) — upstreamable, but heavy maintenance and the bounded
   length still needs the same semantic declaration.

## Forbid

1. Do **not** write "musl has no gets → build failure" as the root cause in
   notes/Issues/drafts — factually wrong (symbol is retained) and it pollutes
   the E093 genus.
2. Do **not** hand-write a `gets()` symbol implementation — revives an API
   removed from C11 for unbounded-unsafety.
3. Do **not** put a global `#define gets` in a shared/public header — it leaks
   into every TU and breaks unrelated code.

## Verification (self-contained, fresh shell on an OHOS device)

```bash
# /tmp on the device is read-only (erofs); $TMPDIR (default
# /storage/Users/currentUser/tmp) is the writable scratch location
/data/service/hnp/bin/llvm-nm -D /lib/ld-musl-aarch64.so.1 | grep -wE "gets|fgets|getline"
printf '#include <stdio.h>\nint main(void){char b[8];gets(b);puts(b);return 0;}' \
  | /data/service/hnp/bin/clang -xc - -o "$TMPDIR/getsprobe" && echo ok | "$TMPDIR/getsprobe"
```

Expected: three T symbols with distinct addresses; probe compiles with
warnings only, runs, and echoes `ok`.

## Related knowledge

- [E093] — reverse genus (musl genuinely missing a function vs declaration
  gating with symbol retained).
- Principles: P-CFLAGS-001 (build-variable fixes preferred over source edits),
  P-PATCH-003 (minimal, explainable, repeatable changes).
