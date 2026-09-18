cmake_minimum_required(VERSION 3.15)
project(test_libgetline C)

# Find the package via Conan-generated CMakeDeps
find_package(libgetline REQUIRED)

add_executable(test_libgetline test.c)
target_link_libraries(test_libgetline libgetline::libgetline)

add_executable(test_libgetline_ohos ohos_platform_test.c)
target_link_libraries(test_libgetline_ohos libgetline::libgetline)

enable_testing()
add_test(NAME consumer COMMAND test_libgetline)
add_test(NAME ohos_platform COMMAND test_libgetline_ohos)