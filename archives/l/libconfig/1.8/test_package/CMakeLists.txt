cmake_minimum_required(VERSION 3.15)
project(test_libconfig C)

find_package(libconfig REQUIRED)

add_executable(test_libconfig test.c)
target_link_libraries(test_libconfig libconfig::libconfig)

configure_file(consumer.cfg consumer.cfg COPYONLY)

enable_testing()
add_test(
    NAME test_libconfig
    COMMAND test_libconfig "${CMAKE_CURRENT_BINARY_DIR}/consumer.cfg"
)
