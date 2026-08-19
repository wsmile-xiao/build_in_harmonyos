cmake_minimum_required(VERSION 3.15)
project(test_fluent_bit C)

# L1 official test: this is an APPLICATION recipe (cpp_info.libs=[]), so we
# don't link against fluent-bit. Instead, the test binary looks up the installed
# `fluent-bit` executable via the FLUENT_BIT_BIN env var (set by conanfile.py)
# and runs `fluent-bit --version` / `--help` to verify the package works.
add_executable(test_fluent_bit test.c)

enable_testing()
add_test(NAME test_fluent_bit COMMAND test_fluent_bit)
