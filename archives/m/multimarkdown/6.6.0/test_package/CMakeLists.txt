cmake_minimum_required(VERSION 3.5)
project(test_multimarkdown C)

find_package(multimarkdown REQUIRED)

add_executable(test_multimarkdown test.c)
target_link_libraries(test_multimarkdown multimarkdown::multimarkdown)

enable_testing()
add_test(NAME test_multimarkdown COMMAND test_multimarkdown)
