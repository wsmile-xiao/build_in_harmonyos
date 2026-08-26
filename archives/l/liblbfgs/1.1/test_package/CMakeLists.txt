cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(liblbfgs CONFIG REQUIRED)

add_executable(test_liblbfgs test.c)
target_link_libraries(test_liblbfgs PRIVATE liblbfgs::liblbfgs)

enable_testing()
add_test(NAME test_liblbfgs COMMAND test_liblbfgs)
