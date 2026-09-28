cmake_minimum_required(VERSION 3.15)
project(test_ctml CXX)

# 通过 Conan CMakeDeps 找到被测包（配方 cmake_file_name=CTML / cmake_target_name=CTML::CTML）
find_package(CTML REQUIRED)

add_executable(test_ctml test.cpp)
target_link_libraries(test_ctml CTML::CTML)

enable_testing()
add_test(NAME test_ctml COMMAND test_ctml)
