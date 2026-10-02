cmake_minimum_required(VERSION 3.15)
project(librtas_test C)

find_package(librtas REQUIRED)

add_executable(librtas_test main.c)
target_link_libraries(librtas_test PRIVATE librtas::librtas)

enable_testing()
add_test(NAME librtas_test COMMAND librtas_test)
