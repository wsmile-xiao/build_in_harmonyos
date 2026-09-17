cmake_minimum_required(VERSION 3.15)
project(test_librcd C)

# 经 Conan CMakeDeps 找到被测包（默认 cmake_file_name = 包名 → find_package(librcd)）。
find_package(librcd REQUIRED)

add_executable(test_librcd test_librcd.c)
target_link_libraries(test_librcd PRIVATE librcd::librcd)

enable_testing()
add_test(NAME test_librcd COMMAND test_librcd)
