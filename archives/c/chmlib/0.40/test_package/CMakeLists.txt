cmake_minimum_required(VERSION 3.5)
project(test_chmlib C)

find_package(chmlib REQUIRED)

add_executable(test_chmlib test_chmlib.c)
target_link_libraries(test_chmlib PRIVATE chmlib::chmlib)

enable_testing()
add_test(NAME test_chmlib COMMAND test_chmlib)
