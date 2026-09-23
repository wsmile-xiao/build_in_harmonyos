cmake_minimum_required(VERSION 3.15)
project(test_libbdplus C)

find_package(libbdplus REQUIRED CONFIG)

add_executable(test_bdplus test_bdplus.c)
target_link_libraries(test_bdplus PRIVATE libbdplus::libbdplus)

enable_testing()
add_test(NAME test_bdplus COMMAND test_bdplus)
