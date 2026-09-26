cmake_minimum_required(VERSION 3.15)
project(test_radcli C)

find_package(radcli REQUIRED)

add_executable(test_radcli test.c)
target_link_libraries(test_radcli radcli::radcli)

enable_testing()
add_test(NAME test_radcli COMMAND test_radcli)
