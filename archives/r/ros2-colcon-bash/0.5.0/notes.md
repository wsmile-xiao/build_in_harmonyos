# ros2-colcon-bash 0.5.0

## Summary

This package provides Bash shell extension support for colcon. The recipe uses
an explicit copy into `lib/python3/site-packages` and writes minimal
`dist-info` metadata, including the `colcon_core.shell` entry point. This avoids
pip build-isolation network access during local builds.

## Tests

The local `test_package` imports `colcon_bash`, checks package metadata version
`0.5.0`, verifies the shipped Bash template resources, and checks the packaged
upstream `test/` files plus `setup.cfg` test dependency metadata.

The release tarball contains three upstream pytest files under `test/`, with
five pytest items total:

- `test_copyright_license.py`: 1 item
- `test_flake8.py`: 1 item
- `test_spell_check.py`: 3 items

The OHOS Python 3.12 runner can reproduce the copyright check and the two
spell wordlist checks without extra modules. A direct audit run with isolated
PyPI test dependencies reached 4/5 passing; `test_flake8.py` failed due
`flake8-import-order` / flake8 / Python 3.12 toolchain drift rather than a
runtime packaging failure. The actual upstream test result is therefore
recorded as `4/5`, not `5/5`. The `test_package` preserves upstream test files
in the package and executes the reproducible package-level checks separately.

## OHOS notes

No native code is compiled. Full runtime use still requires `colcon-core` and
the broader ROS/colcon Python runtime stack on the target system.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`ros2-colcon-bash-0.5.0-upstreamtests-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-0.5.0-ros2-colcon-bash-0.5.0-upstreamtests-r1-conan-20260731-204951-58404`
- Command:
  `zsh ci/conan/build_and_test.sh archives/r/ros2-colcon-bash/0.5.0`
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `ros2-colcon-bash/0.5.0#f5d8797e5c71f6ff30273689aeacbd41:fc3eeb021243959114a0318489539cad6d087e28#4291770f1e1d205a6e26673f05d7dd8e`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L1e=pass`,
  `L2=skip(no bin/ dir)`, `L4=pass(no patches)`, `L5=pass(lib/ has content)`
- Test evidence: `test_package` ran
  `test_ros2_colcon_bash.py` and printed
  `ros2-colcon-bash upstream tests and packaged resources verified`.
- Upstream pytest audit result: `4/5` reproducible checks passed;
  `test_flake8.py` is not counted as passed.

The release tarball upstream tests are packaged under
`share/ros2-colcon-bash/test` for traceability.
