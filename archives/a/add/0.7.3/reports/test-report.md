# add 0.7.3 HarmonyOS test report

## Environment

- Host preparation: Windows worktree with Python and Conan static checks
- Target: HarmonyOS aarch64 real device at `10.62.222.172:2222`
- Device runner: isolated HOME, Conan cache, temporary directory, and global lock
- Conan: 2.29.1
- Rust/Cargo: 1.97.1
- Clang: HarmonyOS profile compiler, version 15

## Dependency result

- Conan package dependencies: none
- Rust git dependencies: none
- Build prerequisite: Rust/Cargo toolchain supplied by the worker
- Linker: Conan profile `tools.build:compiler_executables` C compiler

Result: PASS. No separate dependency-library adaptation is required.

## Local checks

| Check | Result | Evidence |
|---|---|---|
| Source identity | PASS | `keszybz/add-determinism`, tag `v0.7.3`, commit `af17df2c477a48d4a7268c7b9c5ab91a0a19e507` |
| Source SHA256 | PASS | `d1f5eac303807fa31e25b4f8ccb08fed23d15f4ffdbe3bb4ee35a29504c766b2` |
| Recipe and YAML syntax | PASS | Python compile plus structured YAML checks |
| Repository pre-commit | PASS | Exit code 0 on branch `feat/add-0.7.3` |
| Change scope | PASS | Only `archives/a/add/` package files |
| W4 pre-PR audit | PASS | P0=0, P1=0, P2=0, P3=1 documented prerequisite |

## Shadow CI r3

Command:

```sh
CI_PACKAGES=archives/a/add/0.7.3 zsh -f ci/conan/build_and_test.sh
```

Runner: `codex-add-shadow-ci-r3-2283-20260819-173638-48368`

| Check | Result | Evidence |
|---|---|---|
| Conan build | PASS | Build Summary: Total 1, Success 1, Failed 0 |
| Upstream tests | PASS | 863 passed, 17 platform cases filtered, 0 failed |
| Consumer smoke | PASS | 3/3 CLI assertions passed |
| Destructive negative test | PASS | Consumer tests fail without the package under test |
| L0 | PASS | Recipe and archive policy gates passed |
| L1 | PASS | Structured test evidence passed |
| L2 | PASS | Packaged CLI smoke passed |
| L4 | PASS | Static security checks passed |
| L5 | PASS | Packaged artifact baseline passed |

Package reference:

```text
add/0.7.3#5d32313fee0d53b32b56fceadabe6391:6b129b068851896169fae42d399fa922d239ce8a#61b00c7225a24785819b10ab2b15e179
```

Evidence SHA256 values:

- build log: `996568fdfa24847a21c54ca8793f1217924661390c194ea5d284264a6489ebc6`
- Conan log: `26d5a0291119b4c339e672d85cfc945d64b468e1a1441b035923077dc2c435f7`
- metadata: `a5a08807b45e10fb5cb3bbd80e79d69fb12eb925b00855b546a85028e429a4c3`

## Official W3

Runner: `codex-add-finish-w3-r1-2283-20260819-182253-12661`

- Global device-lock wait: 6195 seconds
- G2 clean Conan build: PASS
- G3 same-name system isolation: PASS
- Artifact verification: PASS
- `setup.sh`: PASS
- single-package `build_and_test.sh`: PASS
- generated W3 result: exit code 0, integrity hash `8db1e60aba1f91a9`

The outer finish command returned 1 after W3 because later archive-readiness
and repository-wide knowledge/SUMMARY checks reported warnings. This does not
change the generated W3 result or the package validation outcome.

## Release archive

The ignored local submit-gate archive was made from the official W3 Conan
package folder and contains `bin/`, `licenses/`, and `res/`.

- file: `add-0.7.3-ohos-aarch64.tar.gz`
- size: 3,432,991 bytes
- SHA256: `bfa514f1795b3b3ab812c3d03fbae79c5fb00649a552d94a759070d6518e22de`
- `bin/add-det` SHA256: `5c62c31d4e97bf9f94a795d68e80aefb40363834bab3ffa3853235f6d490a848`
- `bin/linkdupes` SHA256: `8bfe129ed60b3ff571dda948f48dab433928e23b30303010c754d2aeee1edd3a`

## Result

PASS. `add/0.7.3` is ready for PR submission under issue 2283.
