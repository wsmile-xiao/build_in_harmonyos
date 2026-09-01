cmake_minimum_required(VERSION 3.15)
project(test_etl CXX)

# 通过 Conan 生成的 CMakeDeps 查找 etl 包
find_package(etl REQUIRED)

add_executable(test_etl test_etl.cpp)
target_link_libraries(test_etl etl::etl)

enable_testing()
add_test(NAME test_etl COMMAND test_etl)
