cmake_minimum_required(VERSION 3.15)
project(test_libdatovka C)

find_package(libdatovka CONFIG REQUIRED)

add_executable(test_libdatovka test.c)
target_link_libraries(test_libdatovka PRIVATE libdatovka::libdatovka)

enable_testing()
add_test(NAME test_libdatovka COMMAND test_libdatovka)
