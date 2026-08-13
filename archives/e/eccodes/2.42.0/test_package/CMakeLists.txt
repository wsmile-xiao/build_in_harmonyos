cmake_minimum_required(VERSION 3.15)
project(test_eccodes C)

find_package(eccodes REQUIRED)

add_executable(test_eccodes test_eccodes.c)
target_link_libraries(test_eccodes eccodes::eccodes)

enable_testing()
add_test(NAME test_eccodes COMMAND test_eccodes)
