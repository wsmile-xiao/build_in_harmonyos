cmake_minimum_required(VERSION 3.15)
project(test_qoi C)

find_package(qoi REQUIRED)

add_executable(test_qoi test_qoi.c)
target_link_libraries(test_qoi PRIVATE qoi::qoi)

enable_testing()
add_test(NAME test_qoi COMMAND test_qoi)
