# Upstream Test Report: rdiff-backup 2.2.6

## Upstream Inventory

- Main base suite entry: `tox -c tox.ini -e py`.
- Root-only suite entry: `tox -c tox_root.ini -e py`.
- Slow suite entry: `tox -c tox_slow.ini -e py`.
- Fixture setup entry: `tools/setup-testfiles.sh`.

The full upstream runtime suite depends on the external
`rdiff-backup-filesrepo` fixture repository and root/sudo setup to unpack and
fix ownership/device metadata. That complete suite is not counted as passed
until it is actually run in the target environment.

## Executed Package Scope

The recipe runs this upstream base subset before packaging:

- `testing/commontest.py`
- `testing/api_test.py`
- `testing/setconnectionstest.py`
- `testing/timetest.py`
- `testing/iterfiletest.py`
- `testing/hashtest.py`
- `testing/utils_simpleps_test.py`
- `testing/ctest.py`
- `testing/librsynctest.py`
- `testing/action_complete_test.py`
- `testing/location_lock_test.py`
- `testing/action_compare_test.py`
- `testing/action_list_test.py`
- `testing/action_remove_test.py`
- `testing/action_verify_test.py`
- `testing/readonly_actions_test.py`
- `testing/rdb_arguments.py`

This subset validates the installed command entry point, API compatibility,
time parsing, iterator/file wrappers, hash transfer, simple process helpers,
the signed CPython extension import path, librsync integration, selected new
API actions, repository locking, read-only repository operations, and argument
parsing.

## Result

- OHOS `conan create` completed successfully.
- New-port run:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.2.6-rdiff-backup-2.2.6-newport-fix1-conan-20260807-192642-13695`
- Full package reference:
  `rdiff-backup/2.2.6#a877db4b6a0bf4f916873827827327cc:98672d2f9ead97a502de7e1f45bd7e0a193d0471#049b271998a6ef8f652861faceed8927`
- Executed upstream subset:
  - `commontest.py`: import/setup helper, no unittest count.
  - `api_test.py`: 4 tests passed.
  - `setconnectionstest.py`: 1 test passed.
  - `timetest.py`: 12 tests passed.
  - `iterfiletest.py`: 7 tests passed.
  - `hashtest.py`: 3 tests run, 1 skipped by upstream.
  - `utils_simpleps_test.py`: 1 test passed.
  - `ctest.py`: 4 tests passed.
  - `librsynctest.py`: 5 tests passed.
  - `action_complete_test.py`: 1 test passed.
  - `location_lock_test.py`: 2 tests passed.
  - `action_compare_test.py`: 1 test passed.
  - `action_list_test.py`: 3 tests passed.
  - `action_remove_test.py`: 1 test passed.
  - `action_verify_test.py`: 1 test passed.
  - `readonly_actions_test.py`: 3 tests run, 1 skipped by upstream.
  - `rdb_arguments.py`: 3 tests passed.
- Counted upstream result: 52 tests run, 50 passed, 2 skipped.
- Consumer validation: `rdiff-backup --version`, CPython extension imports,
  PyYAML runtime import, librsync signature/delta/patch path, and a local
  `rdiff-backup --new backup` smoke test all passed.
- Optional/root/external-fixture tests are not counted as passed.

## Not Counted

Additional probes on new port 33332 found these boundaries:

- `testing/user_grouptest.py` assumes a system `sync` user, which is absent in
  the standard OHOS runner.
- `testing/fs_abilitiestest.py` uses Linux expectations for ACL/EA and hardlink
  support; the OHOS runner reports ACL/EA off and hardlink unsupported.
- `testing/location_map_filenames_test.py` and `testing/action_regress_test.py`
  restore successfully but fail exact permission comparisons because OHOS
  group permission behavior differs from the Linux fixture expectation.
- Hardlink-specific and external-fixture tests remain outside the counted
  subset unless the runner provides the required filesystem/user metadata.
