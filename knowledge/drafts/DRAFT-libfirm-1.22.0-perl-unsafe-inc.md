# Draft: libfirm 1.22.0 — Perl >= 5.26 '@INC' (PERL_USE_UNSAFE_INC) build generators

> Source event: `libfirm/1.22.0` HarmonyOS PC (aarch64-linux-ohos) adaptation, executor pc2-39.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Building libfirm 1.22.0 with the bundled Makefile fails in the emitter/regalloc
generation steps on hosts with Perl >= 5.26:

```text
do "ir/be/amd64/amd64_spec.pl" failed, '.' is no longer in @INC; did you mean do "./ir/be/amd64/amd64_spec.pl"? at ./ir/be/scripts/generate_emitter.pl line 21.
Fatal error: couldn't do ir/be/amd64/amd64_spec.pl: No such file or directory at ./ir/be/scripts/generate_emitter.pl line 23.
make: *** [Makefile:110: build/gen/ir/be/amd64/gen_amd64_emitter.h] Error 2
```

The vendored perl generators call `do $specfile` with paths relative to the
invoking script's working directory (e.g. `ir/be/amd64/amd64_spec.pl`).
Perl 5.26 removed `.` from `@INC` for security, so the relative `do` fails.

## Root cause

- Upstream `generate_emitter.pl` / `generate_regalloc_if.pl` / `generate_new_opcodes.pl`
  were written for older Perl where the current directory is implicitly in `@INC`.
- Perl >= 5.26 drops `.` from `@INC`; relative `do`/`require` fail.
- This is an environment/toolchain behavior change — not a source defect of the
  generator or of the target library.

## Recommended fix

Set the compatibility env var in the build environment (Conan `generate()`):

```bash
export PERL_USE_UNSAFE_INC=1
```

This restores `.` to `@INC` for legacy scripts without modifying any source file.

## Evidence from libfirm

| Step | Without fix | With PERL_USE_UNSAFE_INC=1 |
|------|-------------|---------------------------|
| `make -j1 CC=clang LINK=clang` | fails at gen_amd64_emitter.h (exit 2) | completes, `libfirm.a` + `libfirm.so` built (exit 0) |
| W3 `conan create` | — | G1/G2/G3/G4 pass |

## Applicability boundary

- Applies to any Makefile-driven C project that invokes vendored Perl code
  generators loading sibling spec files with relative paths.
- The fix is environment-only; no source patch should carry `PERL_USE_UNSAFE_INC`
  changes.

## Counter-examples / limits

- Projects already invoking generators with absolute or `./`-prefixed paths are
  unaffected.
- If the project's own Perl modules are missing (e.g. `Can't locate X.pm in
  @INC`), this env var does NOT help — that is a missing-module problem (E116).

## Related knowledge

- similar_to: E116 (perl module missing), E155 (perl Makefile.PL build)