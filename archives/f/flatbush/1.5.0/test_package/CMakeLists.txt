cmake_minimum_required(VERSION 3.15)
project(test_flatbush CXX)

# 通过 Conan 生成的 CMakeDeps 查找包
find_package(flatbush REQUIRED)

add_executable(test_flatbush test_flatbush.cpp)
target_link_libraries(test_flatbush PRIVATE flatbush::flatbush)

enable_testing()
add_test(NAME test_flatbush COMMAND test_flatbush)
