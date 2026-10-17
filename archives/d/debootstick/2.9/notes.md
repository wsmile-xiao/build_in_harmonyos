# debootstick 2.9 adaptation notes

## Upstream

- Repository: https://github.com/drakkar-lig/debootstick
- Project site: https://drakkar-lig.github.io/debootstick
- Debian tracker: https://tracker.debian.org/pkg/debootstick
- Version: 2.9 (Debian native tarball `debootstick_2.9.tar.xz`)
- License: BSD-3-Clause (`debian/copyright`, CNRS 2014-2015)
- sha256: `6be758f1ee468ba6a90af797e5f2cf02881150cb107c0bcf1796b01f4f6c8566`
  (as recorded in `debootstick_2.9.dsc`)
- Content: `debootstick` launcher (bash), `scripts/` helpers,
  `disk-layouts/` partition layouts, `Makefile` (install only),
  `debootstick.8` man page, `debian/` packaging

## Build system analysis

- Plain Makefile project. `all:` and `clean:` targets are empty; there is
  no configure script and nothing to compile.
- `install-tool` copies `scripts/*` and `disk-layouts/*` to
  `$(DESTDIR)/usr/share/debootstick` and stamps
  `sed 's/@VERSION@/<ver>/' debootstick` into `$(DESTDIR)/usr/sbin/`.
  The version is fished out of `debian/changelog` with sed.
- `install-docs` writes to the absolute path `/usr/share/doc/debootstick`
  (missing `$(DESTDIR)` prefix) and runs `chown root:root` unless
  `DH_BUILD_TYPE=1` is set, so the recipe does not call it.

## OHOS adaptation decisions

| # | Issue | Decision |
|---|-------|----------|
| 1 | Debian native tarball has no top-level directory | `get(..., strip_root=False)` |
| 2 | `install-tool` needs `DH_BUILD_TYPE=1` to skip `chown root:root`, and still targets `usr/sbin` | Replicate the `@VERSION@` stamping in `package()` with Conan `copy`; no make install call |
| 3 | Script shebang is `#!/bin/bash`, absent on OHOS | Recipe `build()` and consumer tests invoke bash via `CONFIG_SHELL` (`/data/service/hnp/bin/bash` fallback); the installed script is called as `bash bin/debootstick ...` |
| 4 | `DBSTCK_DIR` defaults to `/usr/share/debootstick`, missing on consumers | Ship data canonically at `share/debootstick/` AND as sibling copies at `bin/scripts/` + `bin/disk-layouts/`; the upstream `CURRENT_DIR` fallback then resolves with zero source patches |
| 5 | Real image creation needs root, loop devices, parted, grub, and a Debian chroot | Consumer tests stay headless: `--version`, `--help`, `--help-os-support`, two negative CLI paths, and data-file presence checks |

No `patches/` directory: the adaptation is install-layout only and needs no
source modifications.

## Upstream test audit

Upstream ships no automated test suite (see `test_package/MANIFEST.yml`):

- No `tests/`, `test/`, `check/`, `prove`, `pytest`, `ctest`, or `bats` entries
  anywhere in the tree.
- `Makefile` defines only `all` (empty), `clean` (empty), `install*`, and
  `uninstall*`; there is no `check` or `test` target.
- Debian packaging adds no `debian/tests/` autopkgtest.

The recipe `build()` runs `bash -n` syntax checks over the launcher and the
two helpers sourced at startup (`scripts/create-image/cmdline`,
`scripts/create-image/os-detect`). Consumer coverage lives in
`test_package/test.sh` (6 headless scenarios, documented in MANIFEST.yml).

## Verification status

- Local (Windows control plane): recipe tree written; syntax self-review done.
- Real-machine evidence (`conan create` on HarmonyOS aarch64, test_package
  executed/passed counts, upstream-test result line) is pending the HMBS
  preflight round. No pass rates are claimed in advance; the PR body marks
  those fields as pending backfill from the preflight log.
- Falsifiability note for the preflight round: the `--version` test asserts
  the exact string `debootstick 2.9`, so a broken install (missing stamp or
  missing data dir) fails closed instead of passing silently.

## References

- `templates/conanfile-makefile.py.tmpl` (R9/R33 rules)
- `archives/d/dos2unix/7.5.4` (Makefile tool packaging pattern)
- `archives/l/lsof/4.99.3` (tool-type test_package with VirtualRunEnv)
- `knowledge/error-patterns.md` E002 (TMPDIR), E010 (toybox/GNU), E018 (symlink)
