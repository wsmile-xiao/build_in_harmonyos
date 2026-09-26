cmake_minimum_required(VERSION 3.15)
project(cpdb_libs_consumer_test C)

# Conan's generated package configs live outside the SDK sysroot.  Keep them
# discoverable when this consumer test runs under the SDK toolchain locally.
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
find_package(cpdb-libs CONFIG REQUIRED)

add_executable(test_cpdb_libs_ohos test_cpdb_libs_ohos.c)
target_link_libraries(test_cpdb_libs_ohos PRIVATE cpdb-libs::frontend)

enable_testing()
add_test(NAME cpdb_libs_ohos_consumer COMMAND test_cpdb_libs_ohos)
