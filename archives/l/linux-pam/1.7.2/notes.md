# linux-pam 1.7.2 adaptation notes

## Scope

- Issue: 1765
- Worktree: `D:\harmonyos\worktrees\linux-pam`
- Branch: `feat/linux-pam-1.7.2`
- Allowed edit scope: `archives/l/linux-pam/1.7.2/`

## Why this dependency comes first

`pam-wrapper` requires PAM headers and `libpam`/`pam_misc` at build and runtime.
No `linux-pam` or `openpam` package was present in `origin/main`, so this
dependency has to be adapted separately before returning to `pam-wrapper`.

## W0 dependency check

The initial package deliberately avoids optional dependency chains:

- NLS/gettext: disabled
- audit: disabled
- libeconf: disabled
- logind/elogind: disabled
- OpenSSL: disabled
- libpwaccess: disabled
- SELinux: disabled
- NIS/libtirpc/libnsl: disabled
- pam_userdb DB backends: disabled
- pam_unix/libxcrypt/shadow helpers: disabled
- docs/examples/xtests: disabled

The resulting first-pass package is a minimal Linux-PAM provider for downstream
libraries: public headers, `libpam`, `libpam_misc`, `libpamc`, and the pure
`pam_permit.so` module for consumer testing.

`meson/1.11.0` is present in the repository as published metadata. `ninja` is
present but marked partial, so the recipe follows existing Meson package style
and does not add `tool_requires`; the OHOS worker is expected to provide the
build tools.

## Source and build analysis

- Source URL:
  `https://github.com/linux-pam/linux-pam/releases/download/v1.7.2/Linux-PAM-1.7.2.tar.xz`
- SHA256:
  `3d86b6383fb5fd9eb9578d2cd47d92801191f4bf3f9bc61419bfefc8aa1e531a`
- Build system: Meson, minimum Meson 0.62
- Public headers installed under `include/security`
- Core libraries: `pam`, `pam_misc`, `pamc`
- Upstream tests: Meson tests under `tests/`, executed by the recipe with
  `meson test --print-errorlogs` during the default `conan create` build phase

The upstream release tarball stores module `meson.build` files as symlinks to
`../module-meson.build`. Windows `tar` cannot fully materialize those links in
this workspace, but the source package structure is valid for OHOS/Linux.

## Prepared Conan package

The recipe uses MesonToolchain and disables optional platform integrations. It
also injects `llvm-ar`/`llvm-ranlib` into `conan_meson_native.ini` when Conan's
profile provides compiler executable paths, matching the pattern used by other
Meson recipes in this repository.

The recipe runs upstream Meson tests unconditionally after `meson.build()`,
using a `meson.test()` wrapper that executes
`meson test -C "<build_folder>" --print-errorlogs`. This keeps the default CI
path compliant with the upstream-test gate; there is no package option that
disables those tests.

Before configuring, the recipe marks upstream `aux/*.sh` helpers executable so
Meson can launch scripts such as `chdir_meson_build_subdir.sh` under the
HarmonyOS user/group permission model.

The third portability patch also makes Meson invoke that helper through `sh`
instead of direct exec. This preserves the upstream test definitions while
avoiding permission-denied failures on filesystems that do not expose world
execute bits from the unpacked release archive.

The fourth portability patch keeps the upstream `pam_start` core tests isolated
from the device `/etc` PAM configuration. The affected tests use the existing
empty `tests/confdir` service through
`pam_start_confdir(..., getenv("srcdir"), ...)`. This avoids depending on system
PAM state while leaving the packaged libpam runtime configuration path
unchanged.

After `meson.build()`, the recipe materializes `libpam.so.0` in the build tree
before running upstream tests. Meson/HarmonyOS does not create shared-library
symlinks there, but upstream test binaries depend on the SONAME alias at
runtime.

The consumer test is not empty. It:

- compiles against `security/pam_appl.h` and `security/pam_misc.h`
- writes an isolated PAM service under the build folder
- uses installed `pam_permit.so` through an absolute module path
- calls `pam_start_confdir`, `pam_authenticate`, `pam_acct_mgmt`,
  `pam_misc_setenv`, `pam_getenv`, and `pam_end`

## Local verification

Performed locally:

- Downloaded the official release tarball
- Computed SHA256
- Inspected Meson options, dependencies, library targets, module template, and
  upstream test registration
- Prepared `conanfile.py`, `conandata.yml`, minimal module patch, and
  non-empty `test_package`

Not performed locally:

- `conan download/create`: this Windows host has no `conan` command
- OHOS/shadow CI from this Windows host; real-device validation was run later
  through the single-package queue, and must be repeated after enabling
  mandatory upstream Meson tests

## Next steps

On OHOS/shadow, run:

```sh
conan download "meson/1.11.0" -r=ohpcd --only-recipe
CI_PACKAGES="archives/l/linux-pam/1.7.2" zsh ci/conan/build_and_test.sh
```

If the first pass succeeds, return to `pam-wrapper` and add
`self.requires("linux-pam/1.7.2")` there before running its single-package CI.
## OHOS real-device verification

Device run: `/storage/Users/currentUser/ohos-test-runs/codex-linux-pam-linux-pam-linux-pam-1.7.2-1765-r1-conan11-20260804-100641-21320`

Command shape:

```sh
sh "$HOME/bin/ohos-test-runner.sh" --try-lock \
  --user codex-linux-pam \
  --lib linux-pam \
  --task linux-pam-1.7.2-1765-r1-conan11 \
  --mode heavy \
  --workdir /storage/Users/currentUser/ohos-users/codex-linux-pam/linux-pam-1.7.2-1765-r1/repo/build_in_harmonyos \
  --path "$HOME/.local/bin:$HOME/usr/local/bin:/data/service/hnp/bin" \
  -- sh /storage/Users/currentUser/ohos-users/codex-linux-pam/linux-pam-1.7.2-1765-r1/run-linux-pam-ci.sh
```

Result:

- Previous L0: pass
- Previous L1: pass, `test_package` executed and printed `linux-pam pam_permit and pam_misc smoke test passed`; this run predated mandatory upstream `meson test`
- L2: skip, no `bin/` directory for this library package
- L4: pass, patch scan clean
- L5: pass, library artifacts present

Portability fixes found during device validation:

- OHOS exposes `shadow.h` but does not declare `getspnam()`/`getspnam_r()` for this build; the minimal provider returns `NULL` from `pam_modutil_getspnam()` on OHOS because shadow-dependent modules are intentionally disabled.
- The shadow lookup fallback is selected by Meson feature detection (`HAVE_GETSPNAM`), not by an OHOS platform macro.
- Meson cannot create shared-library symlinks on this OHOS filesystem, so the recipe materializes `libpam.so`, `libpam_misc.so`, and `libpamc.so` aliases as regular files for Conan CMakeDeps consumers.

Next downstream step: return to `pam-wrapper/1.1.8` and require `linux-pam/1.7.2`, then run the same single-package OHOS queue for issue #1763.
