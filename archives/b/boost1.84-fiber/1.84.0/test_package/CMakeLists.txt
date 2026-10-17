cmake_minimum_required(VERSION 3.15)
project(test_boost_fiber CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 双包依赖模式（CMakeDeps 实测结论）：fiber 包用独立 cmake_file_name
# "boost1.84-fiber"，context 依赖包持 "Boost"——同 cmake_file_name 撞名时
# conan 2.29 会静默丢弃字母序靠后包的组件，故本测试对 fiber 用独立
# find_package(boost1.84-fiber)，对 context 用全限定组件目标
# boost1.84-fiber::boost_fiber（其 requires 已传递 boost1.84-context::boost_context）
find_package(boost1.84-fiber REQUIRED CONFIG)

add_executable(test_boost_fiber test_boost_fiber.cpp)
target_link_libraries(test_boost_fiber PRIVATE boost1.84-fiber::boost_fiber)
target_link_libraries(test_boost_fiber PRIVATE pthread)

enable_testing()
add_test(NAME boost_fiber_test COMMAND test_boost_fiber)
