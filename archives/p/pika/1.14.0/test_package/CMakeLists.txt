cmake_minimum_required(VERSION 3.15)
project(test_pika C)

find_package(pika REQUIRED)

add_executable(test_pika test.c stubs.c)
target_link_libraries(test_pika PRIVATE pika::pika)

enable_testing()
add_test(NAME pika_core_test COMMAND test_pika)
