cmake_minimum_required(VERSION 3.15)
project(test_libiec61850 C)

# 通过 Conan CMakeDeps 找到被测包
find_package(libiec61850 REQUIRED)

add_executable(test_libiec61850 test_libiec61850.c)
target_link_libraries(test_libiec61850 libiec61850::libiec61850)

enable_testing()
add_test(NAME test_libiec61850 COMMAND test_libiec61850)
