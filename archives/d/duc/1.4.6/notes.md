# duc 1.4.6 Adaptation Notes

## Build Configuration

- Build system: Autotools
- Database backend: sqlite3/3.49.1
- Disabled features: Cairo, X11, and ncurses UI
- Retained feature: command-line disk usage indexing and inspection

## OpenHarmony Adaptation

- The official GitHub Release asset includes `configure`; no target-side autoreconf is needed.
- The official GitHub Release archive includes configure and is verified by SHA-256.
- HMDfs cannot write inside the mode 0700 temporary directory created by config.status.
  The recipe replaces that temporary-directory logic with ordinary mkdir.
- PkgConfigDeps exposes SQLite metadata to configure.

## Validation Status

OpenHarmony aarch64 validation passed on 2026-07-29:

- `ohc-run.py conan-verify duc 1.4.6`: PASS
- Native `conan create`: PASS
- `duc --version`: PASS
- Consumer test: 3/3 assertions passed
- `CI_PACKAGES="archives/d/duc/1.4.6" zsh ci/conan/build_and_test.sh`:
  Total 1, Success 1, Failed 0

The upstream index check passed. Hard-link and md5-dependent checks were skipped because
the tested HarmonyOS filesystem does not support hard links.

- Source download exception: the OpenHarmony device times out on github.com; ghfast.top, gitclone.com, and kkgithub.com are unavailable. The official GitHub Release Asset API is used with the verified release SHA256.

HMDfs temporary-directory permission note: this portability patch intentionally does not use umask 077 when config.status creates its temporary directory. On the OpenHarmony HMDfs device, mode 0700 directories cannot be written by config.status, and chmod cannot restore write access. The directory is only used for short-lived configure/config.status intermediate files and is removed by the upstream trap.
