cmake_minimum_required(VERSION 3.15)
project(test_libfixmath LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libfixmath CONFIG REQUIRED)

add_executable(test_libfixmath_cpp_api test_libfixmath.cpp)
target_link_libraries(test_libfixmath_cpp_api PRIVATE libfixmath::libfixmath)

add_executable(test_libfixmath_ohos_abi test_libfixmath_ohos.c)
target_link_libraries(test_libfixmath_ohos_abi PRIVATE libfixmath::libfixmath)

enable_testing()
add_test(NAME test_libfixmath_cpp_api COMMAND test_libfixmath_cpp_api)
add_test(NAME test_libfixmath_ohos_abi COMMAND test_libfixmath_ohos_abi)
