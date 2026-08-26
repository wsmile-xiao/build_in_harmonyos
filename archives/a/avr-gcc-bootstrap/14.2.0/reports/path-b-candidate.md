# Path B candidate: avr-gcc-bootstrap 14.2.0

Issue: #2245

## Application scope

This submission requests review as a Path B knowledge-extension candidate in
addition to the Path A library adaptation. It does not claim an assigned B
classification or a promoted knowledge-graph entry; both remain subject to
maintainer and competition review.

The reusable topic is:

> Sign build-generated OHOS host ELF files after the compiler links them but
> before a bootstrap build first executes them, while preserving the packaged
> compiler driver and cc1 as native signed ELF files.

The related draft is:

- `knowledge/drafts/DRAFT-avr-gcc-bootstrap-generated-host-elf-signing-2245.kv`
- `knowledge/drafts/DRAFT-avr-gcc-bootstrap-generated-host-elf-signing-2245.md`

## Why the topic is reusable

Compiler and code-generator builds can link host helper executables and execute
them within the same build target. OHOS code signing therefore cannot always be
deferred to `package()` or even to the end of a broad `make` phase. A reusable
solution needs three separate controls:

1. intercept host compiler link outputs and sign only host EXEC/DYN ELF files;
2. place explicit signing barriers before generated tools can first execute;
3. retain final packaged tools as native ELF and validate their package-owned
   runtime components through a consumer build.

The pattern applies beyond AVR GCC to native compiler bootstraps and projects
whose freshly linked code generators are consumed immediately.

## Prior-knowledge check

| Existing entry | Covered topic | Difference from this candidate |
|---|---|---|
| E077 | Re-sign ELF after post-install mutation | Does not cover link-time interception before a generated host tool's first execution |
| E087 | Invoke HMDFS-hosted shell scripts through an interpreter | Reused for wrapper/helper scripts; not claimed as new knowledge |
| E311 | Verify Conan source-folder isolation and `no_copy_source` semantics | Useful for GCC build cost/isolation, but not the signing timing or output classification problem |

Generic hardlink, configure-mode and shell-permission workarounds are explicitly
excluded from the Path B claim.

## Evidence matrix

| Evidence | Result |
|---|---|
| Local recipe/test syntax and source patch application | PASS |
| Independent avr-binutils dependency CI (#2244) | PASS |
| r1-r16 isolated iterations | EXPECTED FAIL/TIMEOUT: isolated signing, HMDFS, target-tool, fixed-point, and multilib scope issues |
| r17 full device build/package | BUILD/PACKAGE PASS; test exposed missing unprefixed target-tool dispatchers |
| Cached-package dispatcher Conan test | PASS: `elf32-avr`, `avr:5`, `main`, `__udivmodhi4` |
| r18 isolated full shadow CI | PASS: exit 0, G0/L0/L1/L2/L5 pass, L4 warning |
| GCC selftest target | EXECUTED; release build reports internal self-tests disabled |
| Eight official torture sources at `-O0` and `-O2` | PASS: 16 compile checks |
| Conan consumer AVR compile/link | PASS: package-owned `avr5/libgcc.a`, 102-byte AVR ELF |
| Final multilib/fixed-point scope | PASS: only `.` and `avr5`; `fixed_point = no` |

Successful run:
`codex-avr-gcc-bootstrap-shadow-ci-r18-2245-20260819-181549-8619`

Tested commit: `19bb09c0ce7c7c45a78d08c89f2e9e27b8d1d7d7`.
The requested Path B classification remains an application for maintainer and
competition review, not a self-assigned classification.

## Reproduction

```sh
CI_PACKAGES="archives/a/avr-gcc-bootstrap/14.2.0" zsh ci/conan/build_and_test.sh
```
