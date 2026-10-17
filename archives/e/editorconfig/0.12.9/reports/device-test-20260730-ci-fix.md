# EditorConfig 0.12.9 CI remediation device test

## Environment

- Device: HarmonyOS PC, AArch64
- Test date: 2026-07-30
- Target: `currentUser@10.62.135.191:2222`
- Runtime directory: `/storage/Users/currentUser/codex-tests/pr3072-editorconfig-ci-fix-v2-20260730`
- Conan recipe revision: `7343448bcf3e287d7038f6022ad5846a`
- Conan package revision: `52f929b61306c38f615d2f1ccee9a6b7`

## Integrity and signing

The two executables and shared library came from the complete CI-remediation
`conan create`. Each file was uploaded to its final HMDFS path, checked against
the local SHA256, signed in place, and made executable after signing.

| File | SHA256 before signing |
|------|-----------------------|
| `test_editorconfig` | `13de5726fa111fb88d5c937f354be6a327b3e5606c6c27d3aa4df9767840633f` |
| `test_editorconfig_unit` | `de6f28f99f2542ca66ff41eed10a7848ac54178e689dd19556822044726a9d8d` |
| `libeditorconfig.so.0` | `52ad2bb4d1082c22e5e06646b03683b8706ffee5ee5a974ed21fd0756348950e` |

## Executed tests

```sh
./test_editorconfig_unit version
./test_editorconfig_unit handle_version
./test_editorconfig_unit conf_filename
./test_editorconfig_unit relative_path_error
./test_editorconfig
```

Result: 5/5 passed. The consumer printed
`EditorConfig 0.12.9 parse consumer passed`.

The captured device log SHA256 is
`CE071E13F3B19F13DE49F3F26D6679E968A4D5C3E0141EE8E7D5CCF0E325D8A0`.

## Boundary

This run binds the package and added unit/consumer tests to the new recipe
revision. Buildbot #11256 had already executed all 197 upstream tests: 177
passed, while 20 multiline cases produced correct output but failed CMake
4.1's line-oriented `PASS_REGULAR_EXPRESSION` evaluation. The portability fix
was reproduced with CMake 4.1 using the trailing-newline-sensitive
`meta_multiline` output and an intentionally incorrect extra line. The correct
output exits 0 and the incorrect output exits 1. A current-head CI rerun remains
the authoritative 197/197 target result.
