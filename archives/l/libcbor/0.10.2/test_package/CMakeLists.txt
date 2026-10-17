cmake_minimum_required(VERSION 3.15)
project(test_libcbor C)

# Find the package via Conan-generated CMakeDeps
find_package(libcbor REQUIRED)

add_executable(test_libcbor test.c)
target_link_libraries(test_libcbor libcbor::libcbor)

add_executable(ohos_special_test ohos_special_test.c)
target_link_libraries(ohos_special_test libcbor::libcbor)

enable_testing()
add_test(NAME test_libcbor COMMAND test_libcbor)
add_test(NAME ohos_special_test COMMAND ohos_special_test)
