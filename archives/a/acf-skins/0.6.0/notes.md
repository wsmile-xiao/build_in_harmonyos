# acf-skins 0.6.0 adaptation notes

The recipe uses the immutable upstream `v0.6.0` tag through the official
GitLab repository API. It reproduces the upstream `WWW_DIST` install list:
five theme directories, `static/reset.css`, and the selected Tango icons. The
result is exactly 81 files: 7 CSS, 5 JavaScript, 62 PNG, and 7 JPEG files.

The package is platform-independent data. No source patch or compilation is
required, and consumers receive `share/acf/www/skins` through both
`cpp_info.resdirs` and `ACF_SKINS_ROOT`.

The upstream aports recipe declares `options="!check" # no test suite`, and
the source has no test target or test directory. Upstream testing is therefore
not applicable with zero upstream tests; this is not reported as “0/0 passed”.

The added consumer test traverses the packaged inventory, parses every PNG and
JPEG signature, verifies all CSS and JavaScript files are non-empty, checks
representative theme content, rejects a deliberately corrupted PNG, and proves
that a missing fault-injection file fails as an I/O error instead of reporting
a false-positive structure rejection.

Validation completed on 2026-08-09:

- Linux x86_64 Conan Release and Debug: all three consumer scenarios passed in
  each configuration.
- DevEco OHOS aarch64: the consumer built successfully as an ELF64 AArch64
  executable.
- HarmonyOS PC emulator (x86_64): the package contained 81 files; the normal
  parser scenario and corrupted-PNG fault-injection scenario passed, while the
  missing-file scenario returned an I/O failure with exit code 1 as expected.
