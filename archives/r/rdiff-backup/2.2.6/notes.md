# rdiff-backup 2.2.6 adaptation notes

## Build environment

- Build system: setuptools
- Build date: 2026-08-05
- Compiler: clang
- Status: built

## Source audit

- Upstream project: https://github.com/rdiff-backup/rdiff-backup
- Release: `2.2.6`
- Source archive: PyPI sdist
- Source SHA256: `d0778357266bc6513bb7f75a4570b29b24b2760348bbf607babfc3a6f09458cf`
- Runtime dependencies: librsync, PyYAML, Python 3.6 or newer.
- Optional metadata dependencies `pylibacl`, `pyxattr`, and `psutil` are not
  enabled in this package.

## Packaging

1. Download and verify the official PyPI source archive.
2. Apply declared Conan patches for POSIX process discovery and OHOS directory
   permission compatibility.
3. Install build-time setuptools helpers into the isolated Conan build folder.
4. Build and install upstream setuptools package into a staging prefix with
   `LIBRSYNC_DIR` pointing at the `librsync/2.3.4` Conan package.
5. Sign the generated CPython extension modules on OHOS.
6. Run `rdiff-backup --version` and an executable upstream base-test subset.
   On OHOS this is enabled when the platform Python shared library is present
   and the extensions can be linked against it; the recipe still verifies the
   installed console script plus signed extension ELF artifacts before running
   imports.
7. Copy the staged tree and GPL license into the Conan package.
8. Run the consumer test through Conan's run environment; OHOS uses the same
   artifact checks against the packaged tree.

## Test evidence

- OHOS 6.0 armv8 host profile:
  - `conan create` completed successfully.
  - Full package reference:
    `rdiff-backup/2.2.6#a877db4b6a0bf4f916873827827327cc:98672d2f9ead97a502de7e1f45bd7e0a193d0471#049b271998a6ef8f652861faceed8927`
  - 2026-08-07 isolated new-port run:
    `/storage/Users/currentUser/ohos-test-runs/codex-a-2.2.6-rdiff-backup-2.2.6-newport-fix1-conan-20260807-192642-13695`
  - Gates: L0 pass, L1 pass, L2 skip (HNP Python refuses cache-path extension
    imports for naked version/help without Conan/Python runenv), L4 pass, L5
    pass.
- Upstream tests:
  - Full tox base suite requires external `rdiff-backup-filesrepo` fixtures and
    root/sudo setup, so it is not expected to run completely in the standard
    OHOS user runner.
  - The package recipe runs the executable base subset after staging and
    signing. On OHOS new port 33332 this executed successfully in `build()`:
    `commontest.py` setup helper, `api_test.py` 4/4,
    `setconnectionstest.py` 1/1, `timetest.py` 12/12,
    `iterfiletest.py` 7/7, `hashtest.py` 2 passed plus 1 upstream skip,
    `utils_simpleps_test.py` 1/1, `ctest.py` 4/4,
    `librsynctest.py` 5/5, `action_complete_test.py` 1/1,
    `location_lock_test.py` 2/2, `action_compare_test.py` 1/1,
    `action_list_test.py` 3/3, `action_remove_test.py` 1/1,
    `action_verify_test.py` 1/1, `readonly_actions_test.py` 2 passed plus
    1 upstream skip, and `rdb_arguments.py` 3/3.
  - Counted upstream base-subset result: 52 tests run, 50 passed, 2 skipped by
    upstream.
- Competition CI:
  - `librsync/2.3.4`, `popt/1.16`, and `pyyaml/6.0.2` resolve from the remote
    registry. CI #14243 reached runtime validation and failed only when HNP
    Python tried to import `rdiff_backup.C` from the staging path; the recipe now
    validates the console wrapper, egg-info entry point, and signed ELF artifacts
    without importing extensions from the Conan/HMDFS cache path.

## Dependencies

- Conan package dependencies:
  - `librsync/2.3.4`
  - `pyyaml/6.0.2`
- Build-only PyPI helpers:
  - setuptools
  - wheel
  - setuptools_scm

## OHOS notes

- CPython extension modules must be linked with the platform Python shared
  library and signed after installation.
- OHOS reports `sys.platform == "ohos"` and `platform.system() == "HarmonyOS"`.
- HNP Python can reject user-path CPython extensions under some
  `/storage/Users/currentUser/.conan2/...` layouts with `Permission denied`.
  This is a deployment/path policy limitation, not a compile/link failure; the
  recipe keeps signed-artifact checks as a guard before runtime imports.
- Runtime upstream-test route assessment (2026-08-07):
  - Route 1 is now the active recipe route on new port 33332. The initial
    failure was `PyModule_Create2: symbol not found` because the extensions were
    not linked with `libpython3.12`. The recipe now links against the platform
    Python shared library when it exists and adds that library directory to the
    upstream-test/run environment. This avoids global `LD_PRELOAD`, so
    subprocesses such as `ps` are not polluted. A clean `conan create` on
    2026-08-07 reached the link-change validation and ran the base subset.
  - OHOS Python `subprocess` with `posix_spawn` does not find user-path
    executables through `PATH` in this runner. `librsynctest.py` needs the
    `librsync` package `bin` directory in `PATH` and is launched through a
    Python runner that disables `subprocess._USE_POSIX_SPAWN`; the test itself
    remains unmodified.
  - Route 2 remains a fallback POC: copying the installed `bin`,
    `lib/python*/site-packages`, and
    `librsync` runtime libraries to a candidate HNP-loadable location before
    running the base subset. Candidate paths are not proven: `$HOME/usr/local`
    and `/storage/Users/currentUser/...`
    may still have the same restriction, while `/data/service/hnp/...` is more
    likely to have a loadable label but may not be writable in PR CI. The first
    POC gate is only `import rdiff_backup.C` and
    `import rdiff_backup._librsync`; run the base subset only if both
    imports succeed from that copied location.
- The device filesystem can create directories whose owner UID differs from the
  running process UID. rdiff-backup's upstream `077` umask can therefore remove
  group traversal from repository metadata directories and block creating
  nested directories. The OHOS patch keeps group access available and masks
  unsupported high permission bits.
- Additional full-suite probes not counted as passed:
  - `user_grouptest.py` expects a system `sync` user.
  - `fs_abilitiestest.py` expects Linux ACL/EA support.
  - `location_map_filenames_test.py` and `action_regress_test.py` fail exact
    permission-bit comparisons after restore because the OHOS runner preserves
    different group permissions.
