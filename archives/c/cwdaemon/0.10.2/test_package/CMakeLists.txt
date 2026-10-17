cmake_minimum_required(VERSION 3.15)
project(test_cwdaemon C)

# CWDAEMON_BIN_PATH / CWDAEMON_LICENSE_PATH are injected as CMakeToolchain
# cache variables from test_package/conanfile.py generate().

add_executable(test_cwdaemon test_cwdaemon.c)

enable_testing()
add_test(NAME test_cwdaemon
         COMMAND test_cwdaemon
                 "${CWDAEMON_BIN_PATH}"
                 "${CWDAEMON_LICENSE_PATH}")
