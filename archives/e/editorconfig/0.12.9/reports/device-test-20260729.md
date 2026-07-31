# EditorConfig 0.12.9 HarmonyOS PC device test

## Environment

- Device: HarmonyOS PC, AArch64
- Test date: 2026-07-29
- Target: `currentUser@10.62.135.191:2222`
- Runtime directory: `/storage/Users/currentUser/codex-tests/pr3072-editorconfig-20260729`
- Dynamic library path: the runtime directory above

## Integrity and signing

The two test executables and `libeditorconfig.so.0` were uploaded with SSH
standard input and `dd`. Local and device SHA256 values matched before each
file was signed in its final HMDFS path.

| File | SHA256 before signing |
|------|-----------------------|
| `test_editorconfig` | `b4682fe6c391e36124c7bef4aed5bda51ca43186387bf0ce6cf5b3d46f77b358` |
| `test_editorconfig_unit` | `40035bfd85aa0ecacbc2f060a2adc3ce4dae12ad2d69eea3d4251e4920e32b74` |
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
`6947EDEE418AA72B197EA47B119740839AC75FE1D3F256F120F27B0573296676`.

## Boundary

This run covers the four added C API unit cases and the Conan parser consumer.
It does not claim execution of the complete 197-case upstream CTest suite.
