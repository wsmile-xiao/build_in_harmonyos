# dh-ros 0.15.0 for OpenHarmony

`dh-ros` provides the `rosbuilder` helper and the Debian debhelper `ros` buildsystem for ROS and ROS 2 packages. The recipe packages the upstream Python implementation, the Perl debhelper plugin, the generated `rosbuilder` command, and its man page.

## Dependencies

- `catkin-pkg/1.1.0` for ROS package metadata parsing and dependency ordering
- `perl/5.42.2.3` for the debhelper buildsystem plugin

## Validation

- Upstream Python pytest suite: all 138 collected tests in `tests/` executed and passed.
- Debian autopkgtest commands: `run-cli` and `run-test-suite` executed; `build-test-package` was not run because the OHOS worker lacks Debian package-build tooling.
- Consumer test: imports the installed API, runs `rosbuilder --detect`, `--build-order`, and `--help` against a real ROS package manifest.
