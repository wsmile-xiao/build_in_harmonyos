cmake_minimum_required(VERSION 3.15)
project(test_libevdevplus CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 经 Conan CMakeDeps 找到被测包（默认 cmake_file_name = 包名）。
find_package(libevdevplus REQUIRED)

add_executable(test_libevdevplus test_libevdevplus.cpp)
target_link_libraries(test_libevdevplus PRIVATE libevdevplus::libevdevplus)

enable_testing()
add_test(NAME test_libevdevplus COMMAND test_libevdevplus)
