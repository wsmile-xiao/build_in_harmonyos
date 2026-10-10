cmake_minimum_required(VERSION 3.15)
project(test_vnlog C)

find_package(vnlog CONFIG REQUIRED)
add_executable(test_vnlog test.c)
target_link_libraries(test_vnlog PRIVATE vnlog::vnlog)

enable_testing()
add_test(NAME test_vnlog COMMAND test_vnlog)
