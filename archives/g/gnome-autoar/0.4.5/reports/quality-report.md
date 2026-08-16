# Quality Report - gnome-autoar 0.4.5

**Verdict**: PASS_DEVICE_WITH_CAPABILITY_SKIPS

## Scope

- Issue: 2147
- Branch: `feat/gnome-autoar-0.4.5-2147`
- Package directory: `archives/g/gnome-autoar/0.4.5`
- Official source SHA256: `838c5306fc38bfaa2f23abe24262f4bf15771e3303fb5dcb74f5b9c7a615dabe`
- Required recipes: 7/7 available from `ohpcd`

## Local validation

- Source and Meson build-system analysis: pass
- Python syntax: pass for the recipe and `test_package`
- YAML parsing and Conan recipe inspection: pass
- Patch applicability against the official source: pass through `conan create`
- `git diff --check`: pass
- Consumer test review: calls public APIs, creates a ZIP, and validates its type and size

The Windows analysis profile cannot build OHOS binaries. Build and runtime
validation were therefore performed in the isolated device job below.

## Device environment

- Endpoint: `currentUser@10.62.218.131:2222`
- Isolated job: `gnome-autoar-0.4.5-2147-shadow-20260814-r1`
- Isolated Conan home: `<job>/conan-home`
- Package selection: `archives/g/gnome-autoar/0.4.5` only
- Runner mode: `heavy --try-lock`

No shared Conan cache, validation repository, runner script, or global runtime
library was modified. Busy-lock attempts exited 75 and were retried after the
active single-package job released the global device lock.

## Adaptation findings

- The installed `pkgconf` selected a stale `libpkgconf.so.7`. The recipe uses a
  build-private copy of the matching `libpkgconf.so.7.0.0` and invokes the
  wrapper through `/bin/sh` because cached scripts cannot be executed directly.
- Cached `glib-mkenums` is invoked through the Python interpreter for the same
  execution-policy reason.
- Meson needs explicit SDK `llvm-ar` and `llvm-ranlib` entries.
- The device sandbox rejects symbolic-link creation, including an isolated
  `ln -s` diagnostic. Each upstream symlink test first runs a runtime capability
  probe and skips only on not-supported or permission-denied; the upstream
  extraction path otherwise triggers a fatal GError overwrite before returning.
- `libarchive/3.8.7` reports that decryption is unsupported because its current
  package has no crypto backend. The two affected tests run first and skip only
  after observing that specific capability error.
- The device has no usable CMake. The consumer test uses Meson, PkgConfigDeps,
  VirtualRunEnv, and the same private pkgconf runtime strategy.

## Iteration summary

- r1, r7, r11: runner lock busy; exit 75 before the build command.
- r2-r4: diagnosed and isolated the stale pkgconf runtime and script execution policy.
- r5: reached GLib code generation; fixed interpreter invocation.
- r6-r9: diagnosed the sandbox symlink restriction and the libarchive crypto gap.
- r10: upstream suite passed; CMake consumer configuration was unavailable.
- r12: Meson consumer configuration reached the missing archiver check.
- r13: complete pass before the whitespace-only `0001` hunk narrowing.
- Review rerun: replaced platform guards with runtime capability probes and passed again.

## Final shadow CI review rerun

- Runner ID: `codex-0.4.5-gnome-autoar-0.4.5-2147-shadow-20260814-r1-conan-20260814-182832-24551`
- Runner exit code: 0
- Upstream Meson result: `1/1 gnome-autoar:test-extract-unit OK`
- GLib cases: 22 total, 18 passed, 0 failed, 4 skipped
- Consumer result: `gnome-autoar 0.4.5 consumer test: OK`
- L0: pass (`all checks passed`)
- L1: pass (`upstream tests + test_package executed`)
- L2: skip (`no bin/ dir`; expected for this library package)
- L4: pass (`patches clean`)
- L5: pass (`lib/ has content`)
- Build summary: Total 1, Success 1, Failed 0

Capability skips:

- `/autoar-extract/test-conflict-overwrite-symlink`: OHOS sandbox blocks symlinks
- `/autoar-extract/test-symlink-parent`: OHOS sandbox blocks symlinks
- `/autoar-extract/test-encrypted`: libarchive has no crypto backend
- `/autoar-extract/test-encrypted-wrong-passphrase`: libarchive has no crypto backend

Conan package reference:

`gnome-autoar/0.4.5#e8ab4aad56b97f5fe6e84bed20e47e82:bb9d1be0eae2ad3143ce25809ca7a579c938ccda#a92966c147c177f3b60b68d8c403fc3a`

Evidence:

- CI metadata: `archives/g/gnome-autoar/0.4.5/ci-metadata.json`
- Runner logs: `/storage/Users/currentUser/ohos-test-runs/codex-0.4.5-gnome-autoar-0.4.5-2147-shadow-20260814-r1-conan-20260814-182832-24551/logs`

## Residual scope

The package is marked `built`, not `published`: this PR prepares the source
recipe and verified package artifacts; publishing remains a maintainer/CI
action. Enabling encrypted ZIP decryption requires a separate libarchive
crypto-capability adaptation and must not be mixed into issue 2147.
