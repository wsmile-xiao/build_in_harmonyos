cmake_minimum_required(VERSION 3.15)
project(cmock_consumer C)

enable_testing()
find_package(cmock CONFIG REQUIRED)

add_executable(cmock_consumer test.c)
target_link_libraries(cmock_consumer PRIVATE cmock::cmock)

add_test(NAME cmock_consumer COMMAND cmock_consumer)
