cmake_minimum_required(VERSION 3.15)
project(cpdb_consumer_test C)

# Conan's generated package configs live outside the SDK sysroot.  Keep them
# discoverable when this consumer test runs under the SDK toolchain locally.
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
find_package(cpdb CONFIG REQUIRED)

add_executable(test_cpdb_ohos test_cpdb_ohos.c)
target_link_libraries(test_cpdb_ohos PRIVATE cpdb::frontend)

enable_testing()
add_test(NAME cpdb_ohos_consumer COMMAND test_cpdb_ohos)
