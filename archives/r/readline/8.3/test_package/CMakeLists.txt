cmake_minimum_required(VERSION 3.5)
project(test_readline C)

find_package(readline REQUIRED)

add_executable(test_readline test_readline.c)
target_link_libraries(test_readline PRIVATE readline::readline)

enable_testing()
add_test(NAME test_readline COMMAND test_readline)
