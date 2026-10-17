cmake_minimum_required(VERSION 3.15)
project(test_libdynamite C)

find_package(libdynamite REQUIRED CONFIG)

add_executable(test_libdynamite test_libdynamite.c)
target_link_libraries(test_libdynamite PRIVATE libdynamite::libdynamite)

enable_testing()
add_test(NAME libdynamite_consumer COMMAND test_libdynamite)
