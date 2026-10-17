cmake_minimum_required(VERSION 3.16)
project(test_courier_unicode C)

find_package(courier-unicode REQUIRED CONFIG)

add_executable(test_courier_unicode test_courier_unicode.c)
target_link_libraries(test_courier_unicode PRIVATE courier-unicode::courier-unicode)

enable_testing()
add_test(NAME test_courier_unicode COMMAND test_courier_unicode)
