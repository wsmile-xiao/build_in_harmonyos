cmake_minimum_required(VERSION 3.15)
project(test_libmowgli-2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libmowgli-2 REQUIRED)

add_executable(test_libmowgli-2 test.c)
target_link_libraries(test_libmowgli-2 libmowgli-2::libmowgli-2)

# HarmonyOS-specific test: validates the OHOS cache-line fallback path
# (patches/0002). Separate independent entry, registered as its own CTest.
add_executable(test_ohos_cacheline test_ohos_cacheline.c)
target_link_libraries(test_ohos_cacheline libmowgli-2::libmowgli-2)

enable_testing()
add_test(NAME test_libmowgli-2 COMMAND test_libmowgli-2)
add_test(NAME test_ohos_cacheline COMMAND test_ohos_cacheline)
