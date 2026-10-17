# words-de 2.1 adaptation notes

The package contains the German Aspell standard-spelling dictionaries and the
separate old-spelling dictionary. Its immutable inputs are
`aspell-de-0.50-2.tar.bz2` and `aspell6-de-alt-2.1-1.tar.bz2` from the official
GNU Aspell dictionary archive.

The standard archive uses the legacy prezip v1 format; the old-spelling archive
uses prezip v2. The recipe decodes both formats without an Aspell executable,
removes Aspell affix flags, converts ISO-8859-1 words to UTF-8, deduplicates,
and writes deterministic bytewise-sorted lists. `ngerman` combines `de-only`,
`de_DE-only`, and `de_CH-only`; `ogerman` comes from `de-alt`; `german` is a
byte-identical alias of `ngerman`.

The source archives ship no test files or test targets (33 and 17 archive
entries respectively). The consumer test validates the two entry counts,
ordering, uniqueness, UTF-8 and new/old spelling distinctions, the alias, and
missing-file handling. Its HarmonyOS-specific scenario cross-compiles the
consumer for OHOS x86_64 and runs it on the HarmonyOS PC emulator.

The lists are data-only resources and require no runtime libraries. Conan
exposes `WORDS_DE_FILE` for the standard-spelling list and
`WORDS_DE_OLD_FILE` for the old-spelling list.

Validation on 2026-09-29: Conan create and consumer tests passed with the
Windows native profile and with OpenHarmony x86_64 and armv8/AArch64 cross
profiles. The OHOS x86_64 consumer also ran successfully on the HarmonyOS PC
emulator. The repository `ohc-run finish` workflow did not pass its W3 local CI
gate on this Windows host: `zsh` is unavailable, so `ci/conan/setup.sh` failed
before the CI script could run. The default ConanVerifier G2 profile also
failed in this host environment; its report is retained under `reports/`.
Therefore there is no `.ci-result.json`, and the repository CI gate is not
reported as passing. AArch64 runtime execution remains unverified because no
device is connected.
---

**编译结束**: 2026-09-29 16:42
**最终状态**: built
