# Path B candidate: avr-binutils 2.43.1

Issue: #2244

## Application scope

This submission requests review as a Path B knowledge-extension candidate in
addition to the Path A library adaptation. It does not claim an assigned B
classification or a promoted knowledge-graph entry; both remain subject to
maintainer and competition review.

The reusable topic is:

> Verify a packaged cross-binutils toolchain on an OHOS host by proving three
> independent properties: the host tools execute from the Conan package, the
> generated files have the requested target architecture, and the consumer
> test fails after the package-owned tools are removed.

The related draft is:

- `knowledge/drafts/DRAFT-ohos-cross-binutils-package-verification-2244.kv`
- `knowledge/drafts/DRAFT-ohos-cross-binutils-package-verification-2244.md`

## Why the topic is reusable

Cross-binutils packages cross two architecture boundaries. Their programs are
native OHOS host executables, while the objects and executables they emit are
for a different target and cannot be run on the host. A version-only smoke test
does not prove target semantics and can silently pass by resolving a system
tool. A target execution test is invalid when no target simulator is present.

The reusable verification pattern combines:

1. absolute paths resolved from the Conan dependency and command version checks;
2. an assemble, link, convert and inspect pipeline for a real target MCU;
3. target-format, architecture, section and symbol assertions; and
4. a destructive negative test after the package `bin`/`lib` content is removed.

This separates host executability, target correctness and package ownership
without pretending that the target program ran on OHOS.

## Prior-knowledge check

| Existing entry | Covered topic | Difference from this candidate |
|---|---|---|
| E077 | Re-sign ELF after post-install mutation | Reused for installed host programs; signing is not claimed as new knowledge |
| E087 | Invoke HMDFS-hosted shell scripts through an interpreter | Reused for compiler wrappers; script execution is not claimed as new knowledge |
| E272 | Run cross-binutils DejaGNU tests on OHOS with Expect and tmpfile fixes | Covers upstream testsuite portability; this candidate covers Conan package ownership and target-artifact consumer validation when target code cannot execute |
| E311 | Verify Conan source-folder isolation and `no_copy_source` semantics | Does not cover cross-tool command ownership or host/target architecture assertions |

GNU triplet recognition, configure permissions, Info-document fallback and ELF
signing are explicitly excluded from the Path B claim.

## Evidence matrix

| Evidence | Result |
|---|---|
| Local recipe/test syntax, source checksum and patch application | PASS |
| Conan inspect/export/source and OHOS dependency graph | PASS |
| Six official no-DejaGNU libiberty checks | PASS |
| Sixteen packaged command version checks | PASS |
| ATmega328P assemble/link/objcopy pipeline | PASS |
| AVR ELF architecture, symbols and size assertions | PASS |
| Intel HEX generation | PASS |
| Destructive package-ownership negative test | PASS |
| True-device single-package Shadow CI G0/L0/L1/L2/L5 | PASS |
| Full DejaGNU target matrix | NOT RUN: optional `runtest` package is not published in the configured Conan remote |

The successful run is
`codex-avr-binutils-shadow-ci-r5-2244-20260817-134800-3191`, using recipe
commit `025ba666fdac38d42d5feefa534388111a3b22ca` and shadow commit
`66a185f1b5dfc310b5a6ba52b891201a9c70a88a`. Skipped tests are not counted as
passes and E272 is not reimplemented in this package.

## Reproduction

```sh
CI_PACKAGES="archives/a/avr-binutils/2.43.1" zsh ci/conan/build_and_test.sh
```
