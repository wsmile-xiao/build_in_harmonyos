# add 0.7.3 HarmonyOS PC adaptation

## Package identity

Issue `2283` is submitted under Conan reference `add/0.7.3`. Its upstream
project is `add-determinism`, release `v0.7.3`:

- upstream: `https://github.com/keszybz/add-determinism`;
- tagged commit: `af17df2c477a48d4a7268c7b9c5ab91a0a19e507`;
- source SHA256: `d1f5eac303807fa31e25b4f8ccb08fed23d15f4ffdbe3bb4ee35a29504c766b2`.

The Conan package name follows the issue and maintainer direction; the source
URL, license, executable names, and upstream attribution retain the canonical
project identity.

## Build and test

The project is a Rust 2021 Cargo application with no Conan package
dependencies. It builds `add-det` and `linkdupes`. The recipe uses the
HarmonyOS clang compiler as the Rust linker and packages both executables under
`bin/`; no upstream source patch is required.

The Conan test package asserts `add-det --version`, `add-det --help`, and
`linkdupes --help`, and fails if either executable is absent.

The target command was:

```sh
CI_PACKAGES=archives/a/add/0.7.3 zsh ci/conan/build_and_test.sh
```

Runner: `codex-add-shadow-ci-r3-2283-20260819-173638-48368` on
`currentUser@10.62.222.172:2222`.

Result:

- `L0`, `L1`, `L2`, `L4`, `L5`: pass;
- upstream tests: 863 passed, 17 filtered, 0 failed;
- consumer test: 3/3 assertions passed;
- build summary: Total 1, Success 1, Failed 0.

Package reference:

```text
add/0.7.3#5d32313fee0d53b32b56fceadabe6391:6b129b068851896169fae42d399fa922d239ce8a#61b00c7225a24785819b10ab2b15e179
```

Evidence hashes:

- build log: `996568fdfa24847a21c54ca8793f1217924661390c194ea5d284264a6489ebc6`;
- Conan log: `26d5a0291119b4c339e672d85cfc945d64b468e1a1441b035923077dc2c435f7`;
- metadata: `a5a08807b45e10fb5cb3bbd80e79d69fb12eb925b00855b546a85028e429a4c3`.

## Environment note

The first isolated-HOME run stopped before Conan loaded because the system
Conan Python module was outside the isolated user site path. The rerun fixed
only the runner environment with:

```sh
PYTHONPATH=/storage/Users/currentUser/.local/lib/python3.12/site-packages
```

It also pre-provisioned the official Rust 1.97.1 arm64 OHOS toolchain outside
the repository. No source, recipe dependency, or infrastructure change was
made for this environment workaround. Seventeen upstream cases requiring
hardlink or birth-time behavior remain filtered as documented platform limits.

## Official W3 and packaging evidence

The official `finish add 0.7.3 built` W3 stage ran under the global device
lock in runner
`codex-add-finish-w3-r1-2283-20260819-182253-12661`. The runner acquired the
lock after 6195 seconds. Its G2 Conan build, G3 isolation check, artifact
verification, `setup.sh`, and single-package `build_and_test.sh` all passed.
The generated `.ci-result.json` records W3 exit code 0 and integrity hash
`8db1e60aba1f91a9`.

The release archive used by the local submit gate was created from that W3
Conan package folder. It contains `bin/add-det`, `bin/linkdupes`, `licenses/`,
and `res/`; its SHA256 is
`bfa514f1795b3b3ab812c3d03fbae79c5fb00649a552d94a759070d6518e22de`.
The archive is intentionally ignored by the repository's packaging rule.

The outer `finish` runner returned 1 only after W3, for archive-readiness and
repository-wide knowledge/SUMMARY checks. The package-local report and release
archive gaps are resolved here; no unrelated knowledge or infrastructure files
are included in this change.

## Completion

COMPLETED. The `add/0.7.3` recipe is ready for PR submission.
