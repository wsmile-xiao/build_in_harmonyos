cmake_minimum_required(VERSION 3.15)
project(test_rsync C)

# RSYNC_BIN is passed by conanfile.py test() — absolute path to rsync binary
set(RSYNC_BIN "rsync" CACHE STRING "Path to rsync binary")

add_executable(test_rsync test.c)

enable_testing()
add_test(NAME test_rsync COMMAND test_rsync)
# Pass RSYNC_PATH to the test binary via CTest environment
set_tests_properties(test_rsync PROPERTIES
    ENVIRONMENT "RSYNC_PATH=${RSYNC_BIN}"
)
