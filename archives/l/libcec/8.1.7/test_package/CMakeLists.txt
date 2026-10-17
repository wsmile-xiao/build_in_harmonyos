cmake_minimum_required(VERSION 3.15)
project(test_libcec C)

# Find the package via Conan-generated CMakeDeps
find_package(libcec REQUIRED)

add_executable(test_libcec test.c)
target_link_libraries(test_libcec libcec::libcec)

add_executable(test_libcec_ohos test_ohos.c)
target_link_libraries(test_libcec_ohos libcec::libcec)

enable_testing()
add_test(NAME test_libcec COMMAND test_libcec)
add_test(NAME test_libcec_ohos COMMAND test_libcec_ohos)