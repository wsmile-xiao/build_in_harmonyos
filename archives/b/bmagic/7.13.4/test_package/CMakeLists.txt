cmake_minimum_required(VERSION 3.15)
project(test_bmagic CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bmagic REQUIRED)

add_executable(test_bmagic test.cpp)
# Release 构建默认注入 -DNDEBUG 会把 assert() 整体剔除（W4 审计 P1）：
# 消费者断言必须真实执行，对测试目标显式取消 NDEBUG
target_compile_options(test_bmagic PRIVATE -UNDEBUG)
target_link_libraries(test_bmagic bm::bm)

enable_testing()
add_test(NAME test_bmagic COMMAND test_bmagic)
