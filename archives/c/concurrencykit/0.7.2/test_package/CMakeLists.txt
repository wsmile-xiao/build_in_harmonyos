cmake_minimum_required(VERSION 3.15)
project(test_concurrencykit C)
find_package(concurrencykit REQUIRED)
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE concurrencykit::concurrencykit)
# CMakeDeps declares concurrencykit::concurrencykit as an INTERFACE IMPORTED
# target, so no IMPORTED_LOCATION / RPATH reaches the test_package binary.
# The dynamic loader then cannot find libck.so.0 (SONAME) at ctest runtime.
# concurrencykit_LIB_DIRS_RELEASE is a CMakeDeps局部变量 populated during
# configure (not a cache var, so DEFINED check misses it). Inject it as a
# raw link flag post-find_package via target_link_options so the value is
# expanded when set, embedding -rpath to the package's lib/ for the SONAME
# lookup to resolve without env var inheritance through cmake -> make ->
# ctest -> test_package.
if(DEFINED concurrencykit_LIB_DIRS_RELEASE AND concurrencykit_LIB_DIRS_RELEASE)
    target_link_options(test_package PRIVATE "-Wl,-rpath,${concurrencykit_LIB_DIRS_RELEASE}")
endif()
enable_testing()
add_test(NAME concurrencykit_smoke COMMAND test_package)
