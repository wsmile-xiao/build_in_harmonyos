cmake_minimum_required(VERSION 3.15)
project(test_libnm C)

find_package(libnm CONFIG REQUIRED)

add_executable(test_libnm test_libnm.c)
target_link_libraries(test_libnm PRIVATE libnm::libnm)

enable_testing()
add_test(NAME test_libnm COMMAND test_libnm)
