cmake_minimum_required(VERSION 3.15)
project(test_execstack C)

# execstack is a CLI application, not a library — no find_package needed.
# The test binary invokes execstack via popen() to verify it runs correctly.
# The EXECSTACK_BIN env var is set by the test harness (conanfile.py).

add_executable(test_execstack test.c)

enable_testing()
add_test(NAME test_execstack COMMAND test_execstack)
