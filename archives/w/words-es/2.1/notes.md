# words-es 2.1 adaptation notes

The package version is `2.1`; its immutable input is GNU Aspell Spanish
dictionary release `aspell6-es-1.11-2` (2010-11-22).

The archive's `es.cwl` is prezip v2 data. The recipe decodes its prefix-delta
records directly, strips each Aspell affix suffix after `/`, converts the
Latin-1 word bytes to UTF-8, and writes a byte-sorted, deduplicated list. The
expected result contains 56,329 entries. No Aspell executable is needed.

The archive has no upstream test target or test executable. This was confirmed
by inspecting the file inventory and `Makefile.pre`; the consumer test is
therefore an added package test, not an upstream test. It checks the installed
resource, exact entry count, sorted uniqueness, UTF-8 Spanish samples, and
absence of affix metadata. `test_package/test_harmony.py` runs the same
consumer binary on HarmonyOS x86_64 and verifies the OS and machine identity.

The recipe marks the Conan package type as `unknown` because Conan 2.29.1 has
no resource-data package type. It exports no library or include directories;
consumers locate the data through `WORDS_ES_FILE`.

## Local verification (2026-09-29)

The decoder unit suite passed 6/6. A full local `conan create` using Windows
x86_64 GCC 14 passed, including the consumer executable. The HarmonyOS SDK
26.0.0 / Clang 15.0.4 cross-builds passed for x86_64 and AArch64; the x86_64
binary also passed the `hdc` emulator test (`machine=x86_64`, 56,329 entries).
The AArch64 binary's ELF machine value was verified, but no AArch64 device was
available for runtime testing.

The repository `finish`/W3 CI simulation did not pass on this Windows host:
the clean-build step requires a `.build-context` tarball path, the verifier
wrapper invokes unavailable `/bin/sh`, and CI setup invokes unavailable
`zsh`. The direct Conan build and consumer test passed independently; W3 is
left unmarked rather than recorded as successful.
---

**编译结束**: 2026-09-29 18:19
**最终状态**: built
