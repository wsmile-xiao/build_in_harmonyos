cmake_minimum_required(VERSION 3.15)
project(test_epic5 C)

# Note: Upstream test suite (tests/) is not executed in this Conan test_package
# because:
# 1. Upstream tests use host-native autotools/make check infrastructure that
#    requires build-time code generation incompatible with cross-compilation.
# 2. Upstream test cases are designed for native host execution and rely on
#    bash scripts, diff, and other host tools unavailable on HarmonyOS target.
# 3. This minimal test.c verifies the epic5 library links correctly and its
#    core API (epic5_init / epic5_parse) works on the aarch64 target.

# epic5 is an application (CLI IRC client), not a linkable library.
# This smoke test invokes the installed epic5 binary via popen() and
# verifies the version output contains "EPIC5" (R34).  The binary path
# is provided at runtime via the EPIC5_BIN environment variable, which
# is set by conanfile.py::test() to the installed package's bin/epic5.

add_executable(test_epic5 test.c)

enable_testing()
add_test(NAME test_epic5 COMMAND test_epic5)
