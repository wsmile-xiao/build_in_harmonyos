cmake_minimum_required(VERSION 3.15)
project(test_cotila CXX)

find_package(cotila REQUIRED)

add_executable(test_cotila test.cpp)
target_link_libraries(test_cotila PRIVATE cotila::cotila)
set_target_properties(test_cotila PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_cotila COMMAND test_cotila)

# 上游官方测试套件（test/ 目录原样拷贝）：76 条编译期 static_assert
# （vector 33 + matrix 32 + scalar 11），编译通过即全部通过；可执行文件
# 运行时再打印确认。上游测试零修改（rule：不改动上游测试用例）。
add_executable(cotila_upstream_tests upstream/test.cpp)
target_link_libraries(cotila_upstream_tests PRIVATE cotila::cotila)
set_target_properties(cotila_upstream_tests PROPERTIES CXX_STANDARD 17)
add_test(NAME cotila_upstream_tests COMMAND cotila_upstream_tests)
