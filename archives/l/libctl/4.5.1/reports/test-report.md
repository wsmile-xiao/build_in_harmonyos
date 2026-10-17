# libctl 4.5.1 target-device test report

Date: 2026-09-25. Task: #8151. Team: 诶，云朵. Candidate path: B (knowledge extension), subject to event review.

## Source and dependency scope

- Upstream release: `libctl-4.5.1.tar.gz` from `NanoComp/libctl`, SHA-256 `fcfeb2f13dda05b560f0ec6872757d9318fdfe8f4bc587eb2053a29ba328ae25`.
- Dependencies resolved from the published OHOS Conan remote: Guile 2.2.7.1, GC 8.2.12, GMP 6.3.0, libffi 3.4.4, libunistring 1.0, and Guile's Libtool dependency. The exact OHOS armv8 binary graph had no `info_invalid` node and required no dependency rebuild.
- The published Guile binary lacks its public `libguile.h` although it contains the `libguile/*` headers. The recipe exports the 2.2.7 upstream umbrella header (SHA-256 `baffa7e9d97488eac7b773ce2858c65d1a127491ae01f9d4ad145937d0bedd82`) locally and installs it with libctl; it does not modify or republish Guile. The header is from the GNU Guile 2.2.7 source as distributed by Debian.

## Actual HarmonyOS PC result

- Device: HarmonyOS PC aarch64 / OHOS 6.0, Clang 15, Conan 2.29.1. Its campus-network IP changes; the private run receipt binds the endpoint, host key, boot ID, UID, and launch process. Do not treat the present IP as permanent.
- Final run ID: `libctl-w3-20260925T092800Z`. The transferred 598,016-byte bundle had SHA-256 `2da2b54dbde96cffa20c0a028e089b7df15b447d72ca69653f4bcf75044a11ba`; independent target readback and all nine input hashes passed. The runner launched once and used a task-local Conan home.
- Command: `conan create <run>/input/recipe --profile:host <run>/input/ohos-profile --profile:build <run>/input/ohos-profile --build='libctl/*' -r=ohpcd`. `LIBCTL_SOURCE_ARCHIVE` bound `source()` to the transferred upstream tarball while Conan still checked the official SHA-256.
- `conan create` returned 0. `make check -j1` ran the upstream `test-prism` case: **1/1 passed**. The installed-package `test_package` compiled, linked, and ran against `libctl::libctl`, initialized Guile, checked absolute-path handling and `vector3_dot`, and printed `LIBCTL_CONSUMER_PASS`: **1/1 executable, two assertions**.
- The frozen Conan log SHA-256 is `dc57864d47ea6db069b708bfadf8672e501d0ba8d7ce0659debf792490d27039`. Final receipt-chain head SHA-256 is `b23f92d905c0aecedfcb78b82882aa26bf9c504c9f4f04f0f99001afbcb8c6ce`. The read-only validator returned `W3_VALIDATOR_PASS`, including release, postrelease, and original-runner absence.
- `upstream-test-evidence.log` is a labeled excerpt of the immutable full Conan log with the Automake `# TOTAL: 1` / `# PASS: 1` / `# FAIL: 0` lines and a derived `1/1 PASS` audit statement; it is not presented as a second independent test run.

## Diagnosed failures and limits

- Earlier unique target runs isolated (1) Autoconf `config.guess` and `config.status` private temporary directories that cannot be written under HMDFS numeric-UID drift, (2) the omitted published Guile umbrella header and an initially omitted Conan `exports_sources` declaration, and (3) missing downstream GMP/GC include paths. Each run was closed without relaunching. The final recipe uses an explicit compatible AArch64 canonical tuple, a task-local group-access `mkdir` in the generated configure template, an exported Guile header, and transitive-header traits.
- The runtime printed GC `PT_GNU_RELRO` warnings while the consumer still exited 0; this report does not claim those warnings are repaired.
- No platform CI result, PR review, merge, registry publication, or score approval is claimed.
