cmake_minimum_required(VERSION 3.15)
project(test_libsigc CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan 生成的 CMakeDeps 查找被测包
find_package(libsigc REQUIRED)

add_executable(test_libsigc test_package.cpp)
target_link_libraries(test_libsigc libsigc::libsigc)

enable_testing()
add_test(NAME test_libsigc COMMAND test_libsigc)
