cmake_minimum_required(VERSION 3.15)
project(test_parg C)

# Find the package via Conan-generated CMakeDeps
find_package(parg REQUIRED)

add_executable(test_parg test.c)
target_link_libraries(test_parg parg::parg)

enable_testing()
# 4 个消费者用例分别注册（PR 正文「鸿蒙特有测试」行取数位置）
add_test(NAME consumer_link COMMAND test_parg link)
add_test(NAME consumer_short COMMAND test_parg short)
add_test(NAME consumer_long COMMAND test_parg long)
add_test(NAME consumer_reorder COMMAND test_parg reorder)
