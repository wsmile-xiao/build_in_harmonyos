# catkin-pkg 1.1.0 for OpenHarmony

`catkin-pkg` is the standalone Python package metadata and workspace utility library used by the ROS build ecosystem. This Conan recipe packages the upstream Python modules and console scripts without introducing C or C++ build dependencies.

## Installation

The Conan package exposes its Python modules through `PYTHONPATH` and its console scripts through `PATH`.

## Validation

- Upstream official test suite: 60 passed, 11 warnings across all 13 test files.
- Consumer integration test: imports `catkin_pkg.package.parse_package_string`, parses package metadata, and validates the result.
- Conan verification and local W3 CI simulation: passed.

Upstream sdist omits `test/util.py` and the `test/data/` fixtures used by three test modules. The complete upstream `1.1.0` tag was used for test execution; production sources and the packaged recipe remain unpatched.
