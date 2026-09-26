cmake_minimum_required(VERSION 3.15)
project(test_libdrpm C)

find_package(drpm REQUIRED)

add_executable(test_drpm test_drpm.c)
target_link_libraries(test_drpm drpm::drpm)

# NOTE: the package defaults to static, so this consumer links statically
# and performs no runtime .so lookup (immune to the stale system
# libdrpm.so.0 and the sandbox's dlopen "Permission denied").

enable_testing()
add_test(NAME test_drpm COMMAND test_drpm)
