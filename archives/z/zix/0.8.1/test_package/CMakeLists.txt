cmake_minimum_required(VERSION 3.15)
project(test_zix C)

find_package(zix REQUIRED CONFIG)

add_executable(test_zix test.c)
set_target_properties(test_zix PROPERTIES
    C_STANDARD 99
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
target_link_libraries(test_zix PRIVATE zix::zix)

enable_testing()
add_test(NAME zix_consumer_api COMMAND test_zix)
