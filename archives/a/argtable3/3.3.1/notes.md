# argtable3 3.3.1 adaptation notes

## Source

- Upstream: https://github.com/argtable/argtable3
- Release: `v3.3.1`
- SHA256: `c08bca4b88ddb9234726b75455b3b1670d7c864d8daf198eaa7a3b4d41addf2c`

## Adaptation

- Build the static library with the upstream CMake project.
- Add the `HarmonyOS` CMake install-directory branch.
- Use `#!/usr/bin/env bash` for the amalgamation helper.
- Treat `dos2unix` as optional because the release archive already has Unix line
  endings.
- Export the `argtable3::argtable3` CMake target and `argtable3` pkg-config name.

## Tests

The recipe enables and runs all three upstream CTest targets:

| Target | Upstream cases | Native Linux result |
|---|---:|---:|
| `test_static` | 170 | 170/170 passed |
| `test_src` | 170 | 170/170 passed |
| `test_amalgamation` | 170 | 170/170 passed |
| **Total** | **510** | **510/510 passed** |

The Conan consumer test adds six deterministic assertions against the packaged
public API. Native Linux `conan create` completed with 6/6 assertions passed.

OHOS `conan create` has not been run locally because the official OHOS toolchain
is not installed in this validation container. The competition CI is the
authoritative OHOS validation.
