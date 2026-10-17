cmake_minimum_required(VERSION 3.15)
project(test_libnfnetlink C)

find_package(libnfnetlink REQUIRED)

add_executable(test_libnfnetlink test.c)
target_link_libraries(test_libnfnetlink libnfnetlink::libnfnetlink)

enable_testing()
add_test(NAME test_libnfnetlink COMMAND test_libnfnetlink)
