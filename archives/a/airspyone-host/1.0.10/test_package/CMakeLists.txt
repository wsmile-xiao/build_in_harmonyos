cmake_minimum_required(VERSION 3.15)
project(test_airspyone_host C)

find_package(airspy REQUIRED)

add_executable(test_airspyone_host src/main.c)
target_link_libraries(test_airspyone_host airspyone-host::airspyone-host)

enable_testing()
add_test(NAME test_airspyone_host COMMAND test_airspyone_host)