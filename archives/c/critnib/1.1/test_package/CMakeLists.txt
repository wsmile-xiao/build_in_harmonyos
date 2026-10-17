cmake_minimum_required(VERSION 3.15)
project(test_critnib C)

find_package(critnib REQUIRED)

add_executable(test_critnib test_critnib.c)
target_link_libraries(test_critnib critnib::critnib)

enable_testing()
add_test(NAME test_critnib COMMAND test_critnib)
