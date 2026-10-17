cmake_minimum_required(VERSION 3.15)
project(test_metalang99 C)

# Find the package via Conan-generated CMakeDeps
find_package(metalang99 REQUIRED)

add_executable(test_metalang99 test_metalang99.c)
target_link_libraries(test_metalang99 metalang99::metalang99)
# C99 — matches upstream tests/CMakeLists.txt (C_STANDARD 99 C_STANDARD_REQUIRED ON).
# metalang99 的断言宏底层用 _Static_assert，这是 Clang/gcc 在 C99 下提供的
# 编译器扩展；-std=c99 -pedantic 实测通过（无 ISO C99 警告/错误）。
target_compile_features(test_metalang99 PRIVATE c_std_99)

enable_testing()
add_test(NAME test_metalang99 COMMAND test_metalang99)
