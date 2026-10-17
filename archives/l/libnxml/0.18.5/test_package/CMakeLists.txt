cmake_minimum_required(VERSION 3.15)
project(test_libnxml C)

find_package(libnxml REQUIRED)

add_executable(test_libnxml test.c)
target_link_libraries(test_libnxml libnxml::libnxml)

enable_testing()
add_test(NAME test_libnxml COMMAND test_libnxml)
