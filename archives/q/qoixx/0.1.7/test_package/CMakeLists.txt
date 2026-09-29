cmake_minimum_required(VERSION 3.16)
project(test_qoixx CXX)

# 通过 Conan CMakeDeps 找到被测包（配方 cmake_file_name=qoixx / cmake_target_name=qoixx::qoixx）
find_package(qoixx REQUIRED)

add_executable(test_qoixx test.cpp)
target_link_libraries(test_qoixx PRIVATE qoixx::qoixx)

# 上游 README 声明需要 C++20（GCC 11 / Clang 12 / MSVC 192+），消费者按 C++20 编译
set_target_properties(test_qoixx PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_qoixx COMMAND test_qoixx)
