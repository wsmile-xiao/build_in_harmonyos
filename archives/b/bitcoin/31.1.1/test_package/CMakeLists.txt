cmake_minimum_required(VERSION 3.15)
project(test_bitcoin CXX)

# bitcoin 31.1 上游要求 C++20（src 头文件依赖 std::endian 等 C++20 特性）
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(bitcoin REQUIRED)

add_executable(test_bitcoin test.cpp)
target_link_libraries(test_bitcoin bitcoin::bitcoin)

enable_testing()
add_test(NAME test_bitcoin COMMAND test_bitcoin)
