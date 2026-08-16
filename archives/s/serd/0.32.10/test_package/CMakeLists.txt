cmake_minimum_required(VERSION 3.15)
project(test_serd C)

find_package(serd REQUIRED CONFIG)

add_executable(test_serd test_serd.c)
target_link_libraries(test_serd PRIVATE serd::serd)

enable_testing()
add_test(NAME serd_c_api COMMAND test_serd)
