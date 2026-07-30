cmake_minimum_required(VERSION 3.15)
project(test_iproute2 C)

# IP_BIN is passed by conanfile.py test() — absolute path to the ip binary.
set(IP_BIN "ip" CACHE STRING "Path to ip binary")

add_executable(test_iproute2 test.c)

enable_testing()
add_test(NAME test_iproute2 COMMAND test_iproute2)
# Expose the ip binary path to the test binary via CTest environment.
set_tests_properties(test_iproute2 PROPERTIES
    ENVIRONMENT "IP_PATH=${IP_BIN}"
)
