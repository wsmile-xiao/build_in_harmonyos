cmake_minimum_required(VERSION 3.15)
project(test_termpaint C)

find_package(termpaint REQUIRED)

add_executable(test_termpaint test.c)
target_link_libraries(test_termpaint termpaint::termpaint)

enable_testing()
add_test(NAME test_termpaint COMMAND test_termpaint)
