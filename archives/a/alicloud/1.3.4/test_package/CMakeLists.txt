cmake_minimum_required(VERSION 3.15)
project(test_alicloud CXX)

find_package(alicloud CONFIG REQUIRED)

add_executable(test_alicloud test_alicloud.cpp)
target_link_libraries(test_alicloud PRIVATE alicloud::alicloud)

enable_testing()
add_test(NAME test_alicloud COMMAND test_alicloud)
