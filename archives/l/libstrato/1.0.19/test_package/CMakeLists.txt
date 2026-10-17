cmake_minimum_required(VERSION 3.15)
project(test_libstrato C)

find_package(StratoHAL REQUIRED)

add_executable(test_libstrato test_libstrato.c)
target_link_libraries(test_libstrato StratoHAL::StratoHAL)

enable_testing()
add_test(NAME test_libstrato COMMAND test_libstrato)
