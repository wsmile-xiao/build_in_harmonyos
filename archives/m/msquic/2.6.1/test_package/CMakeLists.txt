cmake_minimum_required(VERSION 3.15)
project(test_msquic C)

find_package(msquic REQUIRED)

add_executable(test_msquic test.c)
target_link_libraries(test_msquic msquic::msquic)

enable_testing()
add_test(NAME test_msquic COMMAND test_msquic)
