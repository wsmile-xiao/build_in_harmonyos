cmake_minimum_required(VERSION 3.15)
project(test_zimdump C)

# ZIMDUMP_BIN is passed by conanfile.py test() — absolute path to zimdump binary
set(ZIMDUMP_BIN "zimdump" CACHE STRING "Path to zimdump binary")

add_executable(test_zimdump test.c)

enable_testing()
add_test(NAME test_zimdump COMMAND test_zimdump)
# Pass ZIMDUMP_PATH to the test binary via CTest environment
set_tests_properties(test_zimdump PROPERTIES
    ENVIRONMENT "ZIMDUMP_PATH=${ZIMDUMP_BIN}"
)
