# seatd 0.9.3 Shadow CI report

- Issue: `2146`
- Date: `2026-08-14`
- Device: HarmonyOS aarch64 at `10.62.218.131:2222`
- Package: `archives/s/seatd/0.9.3`
- Result: **passed**

## Final run

- RUN_ID: `codex-seatd-seatd-0.9.3-2146-20260814-codex-conan-20260814-150253-44478`
- RUN_DIR:
  `/storage/Users/currentUser/ohos-test-runs/codex-seatd-seatd-0.9.3-2146-20260814-codex-conan-20260814-150253-44478`
- Isolated job:
  `/storage/Users/currentUser/ohos-users/codex/seatd-0.9.3-2146-20260814-codex`
- Start: `2026-08-14 15:02:54 +0800`
- End: `2026-08-14 15:04:25 +0800`
- Exit code: `0`
- Lock: global `--try-lock`, acquired immediately and released by the runner

Command executed inside the isolated repository:

```sh
zsh ci/conan/build_and_test.sh archives/s/seatd/0.9.3
```

The runner supplied an isolated `CONAN_HOME`, `TMPDIR`, `TMPPREFIX`, work directory, and log
directory. The source overlay contained only the seatd version directory from the issue branch.

## Results

| Gate | Result | Evidence |
|---|---|---|
| W0 | pass | no required Conan dependencies |
| L0 | pass | all quality gate checks passed |
| Build | pass | 34 upstream compile/link steps completed with clang 15.0.4 |
| Upstream tests | pass | `linked_list` and `connection`, 2/2 |
| Consumer test | pass | Meson build/link and 15/15 API assertions |
| L1 | pass | upstream tests, test_package, and destructive negative test verified |
| L2 | skip | both CLIs reject `--version/--help`; non-blocking by CI policy |
| L4 | pass | no source patches |
| L5 | pass | packaged `bin/` contains `seatd` and `seatd-launch` |

Packaged artifacts include `lib/libseat.a`, `include/libseat.h`, `lib/pkgconfig/libseat.pc`,
`bin/seatd`, and `bin/seatd-launch`. Package revision:
`68b635de49290ff67dcff9a64cc4e276`.

## Consumer assertions

The executable printed `15/15 checks passed`. It covered argument validation, explicit backend
selection, error logging, noop seat lifecycle, pollable fd exposure, dispatch callback behavior,
temporary-device open/close, missing-device `ENOENT`, and final seat cleanup.

## Iterations

1. `...-142634-4183`: exit `75`; active global lock, no build started.
2. `...-142936-12243`: build, upstream tests, and packaging passed; device had no CMake for the
   consumer test.
3. `...-143947-17862`: Meson consumer reached configure; missing `llvm-ar` in generated native
   file.
4. `...-144638-22417`: exit `75`; active global lock, no build started.
5. `...-145714-40064`: Meson consumer reached dependency lookup; device had no pkg-config.
6. `...-150253-44478`: self-contained Meson consumer passed without CMake or pkg-config.

The final test_package obtains the installed include/lib paths from Conan, uses Meson's compiler
library lookup, and injects sibling SDK `llvm-ar`/`llvm-ranlib` for OHOS.

## Evidence hashes

- Runner stdout log SHA-256:
  `4a4ba8fd97fd7f03d585d5064cf0596971ed48f9769fd100902051940df08615`
- Conan build log SHA-256:
  `a4da1cd3c43842988d5e2cf01a6a5327afcc74f1e641dfd2d8b5424ebcc3467c`
- Generated ci-metadata SHA-256:
  `9e5a3e43aef7ebb775ee0acd12eb35bd97fe846139797727e1a14db20fe9dbe0`

## Remaining boundaries

- The upstream `poller` test remains excluded because existing OHOS evidence shows an indefinite
  block. Run it separately under `timeout 30s`.
- Device-node and DRM/input permission behavior for the real seatd daemon was not exercised by the
  unprivileged consumer test.
